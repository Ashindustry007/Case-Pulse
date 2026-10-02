"""Cited fact extraction (F3/F4/F7): injuries + severity, coverage, key dates, treatment visits, provider requests,
client photo. Claude returns structured output with evidence quotes; every quote is VERIFIED against the source text
(rag.cite.verify_quote) and facts without verified evidence are dropped — never shown as facts.

Results are cached by an input hash over the candidate sources; written to `facts` (one row per fact, read by the
brief and by Dev 2's provider projection) and to `briefs(kind='extraction')`.

facts.kind values (contract for readers): injury | coverage | date_of_incident | statute_of_limitations |
date_of_birth | treatment_visit | client_photo
  coverage.value = {"field": carrier|bi_per_person|bi_per_accident|um_uim|medpay, "value": "<text>"}
  injury.value   = {"name","body_region","severity_tier","primary","description"}
  treatment_visit.value = {"provider_contact_id","provider_name","date","description","missed": bool}
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from ..config import settings
from ..db import jdump, jload, now_iso
from ..llm import call_claude_parsed, log_cache_hit
from ..rag.cite import record_citation, verify_quote
from ..rag.search import Hit, hybrid_search
from .context import context_block, matter_context

log = logging.getLogger("casepulse.extract")
EXTRACT_VERSION = "x1"


class Evidence(BaseModel):
    source_id: str = Field(description='The id attribute of the <source> the quote comes from, e.g. "S12"')
    quote: str = Field(description="Exact contiguous text copied from that source (5-40 words)")


class InjuryX(BaseModel):
    name: str
    body_region: str | None
    severity_tier: Literal["soft_tissue", "objective", "surgical"]
    primary: bool
    description: str | None
    evidence: list[Evidence]


class CoverageFieldX(BaseModel):
    value: str
    evidence: list[Evidence]


class DateX(BaseModel):
    value: str = Field(description="ISO date YYYY-MM-DD")
    evidence: list[Evidence]


class VisitX(BaseModel):
    provider_name: str
    date: str = Field(description="ISO date YYYY-MM-DD of the visit / date of service")
    description: str | None
    missed: bool = Field(description="True if the item says the client missed/no-showed/cancelled this visit")
    evidence: list[Evidence]


class MedicalX(BaseModel):
    injuries: list[InjuryX]
    treatment_visits: list[VisitX]


class CoverageX(BaseModel):
    carrier: CoverageFieldX | None
    bi_per_person: CoverageFieldX | None
    bi_per_accident: CoverageFieldX | None
    um_uim: CoverageFieldX | None
    medpay: CoverageFieldX | None
    date_of_incident: DateX | None
    statute_of_limitations: DateX | None
    date_of_birth: DateX | None = Field(description="The CLIENT's date of birth only")


class RequestX(BaseModel):
    provider_contact_id: int
    kind: Literal["records", "bills", "authorization", "other"]
    description: str = Field(description="<= 15 words, neutral, what the firm needs from the provider's office")
    requested_at: str | None
    still_outstanding: bool
    evidence: list[Evidence]


class RequestsX(BaseModel):
    requests: list[RequestX]


GROUNDING = ("Use ONLY the provided sources. Every fact needs evidence: copy an exact contiguous quote from the "
             "source it comes from and give that source's id. If something is not in the sources, return null / an "
             "empty list — never guess or infer amounts, dates or limits.")


# ------------------------------------------------------------------------------------------------------------------
class Sources:
    """Numbered sources shown to the model; maps ids back to (record_id, page)."""

    def __init__(self) -> None:
        self.items: dict[str, tuple[str, int | None]] = {}
        self.parts: list[str] = []
        self._seen: set[tuple[str, int | None, int]] = set()

    def add_hit(self, h: Hit) -> None:
        key = (h.record_id, h.page, h.char_start)
        if key in self._seen:
            return
        self._seen.add(key)
        sid = f"S{len(self.items) + 1}"
        self.items[sid] = (h.record_id, h.page)
        page = f' page="{h.page}"' if h.page else ""
        self.parts.append(f'<source id="{sid}" type="{h.type}" title="{h.title}" date="{h.date or ""}"{page}>\n'
                          f"{h.text}\n</source>")

    def add_record(self, row: sqlite3.Row) -> None:
        key = (row["id"], None, -1)
        if key in self._seen:
            return
        self._seen.add(key)
        sid = f"S{len(self.items) + 1}"
        self.items[sid] = (row["id"], None)
        self.parts.append(f'<source id="{sid}" type="{row["type"]}" title="{row["title"]}" '
                          f'date="{row["occurred_at"] or ""}">\n{row["body_text"]}\n</source>')

    def text(self) -> str:
        return "\n\n".join(self.parts)

    def hash(self) -> str:
        return hashlib.sha256(self.text().encode()).hexdigest()

    def cite(self, db: sqlite3.Connection, evidence: list[Evidence]) -> list[dict]:
        out = []
        for ev in evidence:
            src = self.items.get(ev.source_id.strip())
            if not src:
                continue
            c = verify_quote(db, src[0], src[1], ev.quote)
            if c:
                out.append(c.model_dump(mode="json"))
        return out


def _gather(db: sqlite3.Connection, matter_id: int, queries: list[str], *, types: list[str] | None = None,
            k: int = 8, limit: int = 40) -> list[Hit]:
    seen, out = set(), []
    for q in queries:
        for h in hybrid_search(db, matter_id, q, types=types, k=k):
            if h.chunk_id not in seen:
                seen.add(h.chunk_id)
                out.append(h)
    return out[:limit]


def _cached(db: sqlite3.Connection, matter_id: int, kind: str, h: str) -> dict | None:
    row = db.execute("SELECT content FROM briefs WHERE matter_id=? AND kind=? AND input_hash=?",
                     (matter_id, kind, h)).fetchone()
    return json.loads(row["content"]) if row else None


def _store(db: sqlite3.Connection, matter_id: int, kind: str, h: str, content: dict) -> None:
    db.execute("INSERT OR REPLACE INTO briefs(matter_id, kind, input_hash, content, created_at) VALUES (?,?,?,?,?)",
               (matter_id, kind, h, jdump(content), now_iso()))


def _replace_facts(db: sqlite3.Connection, matter_id: int, kinds: tuple[str, ...], rows: list[tuple[str, dict, list]],
                   h: str) -> None:
    db.execute(f"DELETE FROM facts WHERE matter_id=? AND kind IN ({','.join('?' * len(kinds))})", (matter_id, *kinds))
    for kind, value, cits in rows:
        if cits:  # F3: a fact without a verified citation is never stored
            db.execute("""INSERT INTO facts(matter_id, kind, value, citations, input_hash, model, created_at)
                          VALUES (?,?,?,?,?,?,?)""", (matter_id, kind, jdump(value), jdump(cits), h,
                                                      settings.model_main, now_iso()))


def _providers(db: sqlite3.Connection, matter_id: int) -> list[sqlite3.Row]:
    return db.execute("""SELECT c.id, c.name, c.email, mc.relationship FROM matter_contacts mc
                         JOIN contacts c ON c.id = mc.contact_id WHERE mc.matter_id=? AND mc.role='medical_provider'""",
                      (matter_id,)).fetchall()


def match_provider(providers: list[sqlite3.Row], name: str) -> sqlite3.Row | None:
    if not providers or not name:
        return None
    best = process.extractOne(name, [p["name"] for p in providers], scorer=fuzz.token_set_ratio, score_cutoff=70)
    return providers[best[2]] if best else None


# ------------------------------------------------------------------------------------------------------------------
def extract_medical(db: sqlite3.Connection, matter_id: int, ctx: str) -> dict:
    hits = _gather(db, matter_id, [
        "diagnosis impression assessment injuries", "MRI CT X-ray imaging findings impression",
        "chief complaint pain after collision accident", "surgery recommended procedure surgical consult",
        "date of service visit treatment physical therapy session", "fracture herniation tear sprain strain",
        "missed appointment no show cancelled visit"], k=8, limit=45)
    src = Sources()
    for h in hits:
        src.add_hit(h)
    for r in db.execute("SELECT * FROM records WHERE matter_id=? AND type IN ('medical_record','medical_bill') "
                        "AND deleted_at IS NULL", (matter_id,)):
        src.add_record(r)
    h = hashlib.sha256(f"{EXTRACT_VERSION}|medical|{src.hash()}".encode()).hexdigest()
    if (cached := _cached(db, matter_id, "extract_medical", h)) is not None:
        log_cache_hit("extract", settings.model_main, matter_id=matter_id)
        return cached
    if not src.items:
        result = {"injuries": [], "visits": []}
    else:
        parsed, _ = call_claude_parsed(
            "extract", settings.model_main, MedicalX, matter_id=matter_id, max_tokens=16000,
            output_config={"effort": "low"},
            system=f"You extract medical facts from a personal-injury case file. {GROUNDING}",
            messages=[{"role": "user", "content": (
                f"{ctx}\n\nSources:\n{src.text()}\n\nExtract (1) the CLIENT's injuries/diagnoses — mark the most "
                "significant one(s) primary; severity_tier: soft_tissue (sprains/strains/contusions), objective "
                "(imaging-confirmed: herniation, fracture, tear), surgical (surgery performed or recommended); and "
                "(2) every treatment visit / date of service with the provider name, flagging missed visits.")}])
        providers = _providers(db, matter_id)
        injuries = []
        for inj in parsed.injuries:
            cits = src.cite(db, inj.evidence)
            if cits:
                injuries.append({"value": inj.model_dump(exclude={"evidence"}), "citations": cits})
        visits = []
        for v in parsed.treatment_visits:
            cits = src.cite(db, v.evidence)
            if cits:
                p = match_provider(providers, v.provider_name)
                visits.append({"value": {"provider_contact_id": p["id"] if p else None,
                                         "provider_name": p["name"] if p else v.provider_name, "date": v.date,
                                         "description": v.description, "missed": v.missed}, "citations": cits})
        result = {"injuries": injuries, "visits": visits}
    _store(db, matter_id, "extract_medical", h, result)
    _replace_facts(db, matter_id, ("injury", "treatment_visit"),
                   [("injury", i["value"], i["citations"]) for i in result["injuries"]]
                   + [("treatment_visit", v["value"], v["citations"]) for v in result["visits"]], h)
    db.commit()
    return result


def extract_coverage(db: sqlite3.Connection, matter_id: int, ctx: str) -> dict:
    hits = _gather(db, matter_id, [
        "bodily injury liability limits per person per accident", "declarations page policy coverage insurance",
        "uninsured underinsured motorist UM UIM coverage", "medical payments MedPay PIP coverage",
        "insurance carrier claim number policy number adjuster", "coverage confirmed accepted liability",
        "date of incident accident date of loss", "statute of limitations deadline", "date of birth DOB"],
        k=6, limit=45)
    src = Sources()
    for r in db.execute("SELECT * FROM records WHERE matter_id=? AND type IN ('custom_field') AND deleted_at IS NULL",
                        (matter_id,)):
        src.add_record(r)
    for r in db.execute("""SELECT r.* FROM records r JOIN matter_contacts mc ON r.id = 'contact:' || mc.contact_id
                           WHERE mc.matter_id=? AND mc.role IN ('client','insurer') AND r.deleted_at IS NULL""",
                        (matter_id,)):
        src.add_record(r)
    for h_ in hits:
        src.add_hit(h_)
    h = hashlib.sha256(f"{EXTRACT_VERSION}|coverage|{src.hash()}".encode()).hexdigest()
    if (cached := _cached(db, matter_id, "extract_coverage", h)) is not None:
        log_cache_hit("extract", settings.model_main, matter_id=matter_id)
        return cached
    result: dict = {}
    if src.items:
        parsed, _ = call_claude_parsed(
            "extract", settings.model_main, CoverageX, matter_id=matter_id, max_tokens=8000,
            output_config={"effort": "low"},
            system=f"You extract insurance coverage and key dates from a personal-injury case file. {GROUNDING}",
            messages=[{"role": "user", "content": (
                f"{ctx}\n\nSources:\n{src.text()}\n\nExtract the liability carrier behind the at-fault party, BI "
                "limits per person and per accident, UM/UIM limits, MedPay/PIP limits (values as written, e.g. "
                "\"$100,000\"), the date of incident, the statute of limitations date, and the CLIENT's date of birth.")}])
        for field in ("carrier", "bi_per_person", "bi_per_accident", "um_uim", "medpay", "date_of_incident",
                      "statute_of_limitations", "date_of_birth"):
            val = getattr(parsed, field)
            if val is not None:
                cits = src.cite(db, val.evidence)
                if cits:
                    result[field] = {"value": val.value, "citations": cits}
    _store(db, matter_id, "extract_coverage", h, result)
    rows = [("coverage", {"field": f, "value": result[f]["value"]}, result[f]["citations"])
            for f in ("carrier", "bi_per_person", "bi_per_accident", "um_uim", "medpay") if f in result]
    rows += [(f, {"value": result[f]["value"]}, result[f]["citations"])
             for f in ("date_of_incident", "statute_of_limitations", "date_of_birth") if f in result]
    _replace_facts(db, matter_id, ("coverage", "date_of_incident", "statute_of_limitations", "date_of_birth"), rows, h)
    db.commit()
    return result


def extract_requests(db: sqlite3.Connection, matter_id: int, ctx: str) -> list[dict]:
    providers = _providers(db, matter_id)
    if not providers:
        return []
    src = Sources()
    cand = db.execute("""SELECT * FROM records WHERE matter_id=? AND deleted_at IS NULL AND (
                           type='medical_record' OR (type='task' AND COALESCE(json_extract(meta,'$.status'),'')
                             NOT IN ('complete','completed'))
                           OR type='communication') ORDER BY occurred_at DESC LIMIT 60""", (matter_id,)).fetchall()
    for r in cand:
        src.add_record(r)
    for h_ in _gather(db, matter_id, ["request records itemized bill authorization from provider",
                                      "please send medical records", "HIPAA authorization signed"],
                      types=["note", "communication", "task"], k=6, limit=15):
        src.add_hit(h_)
    plist = "\n".join(f"- provider_contact_id={p['id']}: {p['name']} ({p['relationship'] or 'medical provider'})"
                      + (f" <{p['email']}>" if p["email"] else "") for p in providers)
    h = hashlib.sha256(f"{EXTRACT_VERSION}|requests|{plist}|{src.hash()}".encode()).hexdigest()
    if (cached := _cached(db, matter_id, "extract_requests", h)) is not None:
        log_cache_hit("extract", settings.model_main, matter_id=matter_id)
        return cached["requests"]
    parsed, _ = call_claude_parsed(
        "extract", settings.model_main, RequestsX, matter_id=matter_id, max_tokens=8000,
        output_config={"effort": "low"},
        system=f"You find what a law firm still needs from each treating medical provider's office. {GROUNDING}",
        messages=[{"role": "user", "content": (
            f"{ctx}\n\nTreating providers:\n{plist}\n\nSources:\n{src.text()}\n\nList each item the firm has asked a "
            "provider's office for (medical records, itemized bills, authorizations, narratives...) with the "
            "provider_contact_id from the list. still_outstanding=false if the sources show it was received or the "
            "task was completed.")}])
    valid = {p["id"] for p in providers}
    out = []
    for rq in parsed.requests:
        if not rq.still_outstanding or rq.provider_contact_id not in valid:
            continue
        cits = src.cite(db, rq.evidence)
        if not cits:
            continue
        src_rec = db.execute("SELECT type, participants FROM records WHERE id=?", (cits[0]["record_id"],)).fetchone()
        addressed = False
        channel = {"task": "task", "communication": "email", "medical_record": "records_request"}.get(
            src_rec["type"] if src_rec else "", "note")
        if src_rec and src_rec["type"] == "communication":
            addressed = any(p.get("id") == rq.provider_contact_id and p.get("direction") == "to"
                            for p in jload(src_rec["participants"], []) or [])
        pname = next((p["name"] for p in providers if p["id"] == rq.provider_contact_id), None)
        rid = hashlib.sha256(f"{matter_id}|{rq.provider_contact_id}|{rq.kind}|{cits[0]['record_id']}".encode()).hexdigest()[:16]
        out.append({"id": f"req:{rid}", "provider_contact_id": rq.provider_contact_id, "provider_name": pname,
                    "kind": rq.kind, "description": rq.description, "requested_at": rq.requested_at,
                    "channel": channel, "addressed": addressed, "citations": cits})
    _store(db, matter_id, "extract_requests", h, {"requests": out})
    db.execute("DELETE FROM provider_requests WHERE matter_id=?", (matter_id,))
    for r in out:
        db.execute("""INSERT OR REPLACE INTO provider_requests(id, matter_id, provider_contact_id, provider_name, kind,
                        description, requested_at, channel, source_addressed_to_provider, citations, input_hash,
                        created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                   (r["id"], matter_id, r["provider_contact_id"], r["provider_name"], r["kind"], r["description"],
                    r["requested_at"], r["channel"], int(r["addressed"]), jdump(r["citations"]), h, now_iso()))
    db.commit()
    return out


class PhotoCheck(BaseModel):
    is_photo_of_person: bool = Field(description="A real photograph (not a scan/form) showing a person")
    is_portrait: bool = Field(description="Head-and-shoulders style photo suitable as a profile picture")


def find_client_photo(db: sqlite3.Connection, matter_id: int) -> dict | None:
    """Contact avatar if Clio has one; else the first image document that vision confirms is a portrait."""
    client = db.execute("""SELECT c.id, c.avatar_url FROM matter_contacts mc JOIN contacts c ON c.id=mc.contact_id
                           WHERE mc.matter_id=? AND mc.is_client=1""", (matter_id,)).fetchone()
    imgs = db.execute("""SELECT r.id, r.title, r.content_hash, p.image_path FROM records r
                         JOIN document_pages p ON p.document_id = r.id AND p.page_no = 1
                         WHERE r.matter_id=? AND r.type='document' AND r.deleted_at IS NULL AND
                           (lower(json_extract(r.meta,'$.content_type')) LIKE 'image/%' OR lower(r.title) GLOB
                            '*.[jp][pn]*g')""", (matter_id,)).fetchall()
    h = hashlib.sha256(("|".join(f"{i['id']}:{i['content_hash']}" for i in imgs)
                        + f"|{client['avatar_url'] if client else ''}").encode()).hexdigest()
    if (cached := _cached(db, matter_id, "client_photo", h)) is not None:
        return cached or None
    result: dict = {}
    if client and client["avatar_url"]:
        result = {"source": "clio_avatar", "url": client["avatar_url"], "contact_id": client["id"]}
    else:
        for img in imgs:
            if not img["image_path"] or not Path(img["image_path"]).exists():
                continue
            data = base64.standard_b64encode(Path(img["image_path"]).read_bytes()).decode()
            parsed, _ = call_claude_parsed("vision", settings.model_fast, PhotoCheck, matter_id=matter_id,
                                           max_tokens=500, messages=[{"role": "user", "content": [
                                               {"type": "image", "source": {"type": "base64",
                                                                            "media_type": "image/png", "data": data}},
                                               {"type": "text", "text": "Classify this image."}]}])
            if parsed.is_photo_of_person and parsed.is_portrait:
                result = {"source": "document", "document_id": img["id"]}
                break
    _store(db, matter_id, "client_photo", h, result)
    db.execute("DELETE FROM facts WHERE matter_id=? AND kind='client_photo'", (matter_id,))
    if result.get("document_id"):
        c = record_citation(db, result["document_id"])
        _replace_facts(db, matter_id, ("client_photo",), [("client_photo", result, [c.model_dump(mode="json")])], h)
    db.commit()
    return result or None


def extract_all(db: sqlite3.Connection, matter_id: int) -> dict:
    ctx = context_block(matter_context(db, matter_id))
    out: dict = {}
    for name, fn in (("medical", extract_medical), ("coverage", extract_coverage), ("requests", extract_requests)):
        try:
            res = fn(db, matter_id, ctx)
            out[name] = len(res) if isinstance(res, (list, dict)) else 0
        except Exception as e:  # noqa: BLE001
            log.warning("extract %s failed: %s", name, e)
            out[name] = f"error: {e}"[:200]
    try:
        out["client_photo"] = bool(find_client_photo(db, matter_id))
    except Exception as e:  # noqa: BLE001
        out["client_photo"] = f"error: {e}"[:200]
    return out
