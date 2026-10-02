"""Brief generation (cached by input hash in `briefs`): F2 key moments, story-so-far, F1 delta summary,
suggested questions. Nothing is regenerated unless its inputs (record/digest hashes) changed (F9)."""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3

from pydantic import BaseModel, Field

from ..config import settings
from ..contracts import Citation, CitedSentence, KeyMoment
from ..db import jdump, jload, now_iso
from ..llm import call_claude_parsed, log_cache_hit
from ..rag.answer import cited_generation
from ..rag.cite import record_citation, verify_quote
from ..rag.search import Hit, hydrate
from .context import context_block, matter_context

log = logging.getLogger("casepulse.brief")
BRIEF_VERSION = "b1"
MOMENT_MIN_IMPORTANCE = 6


def _cache_get(db: sqlite3.Connection, matter_id: int, kind: str, h: str):
    row = db.execute("SELECT content FROM briefs WHERE matter_id=? AND kind=? AND input_hash=?",
                     (matter_id, kind, h)).fetchone()
    return json.loads(row["content"]) if row else None


def _cache_put(db: sqlite3.Connection, matter_id: int, kind: str, h: str, content) -> None:
    db.execute("INSERT OR REPLACE INTO briefs(matter_id, kind, input_hash, content, created_at) VALUES (?,?,?,?,?)",
               (matter_id, kind, h, jdump(content), now_iso()))
    db.commit()


def latest(db: sqlite3.Connection, matter_id: int, kind: str):
    row = db.execute("SELECT content FROM briefs WHERE matter_id=? AND kind=? ORDER BY created_at DESC LIMIT 1",
                     (matter_id, kind)).fetchone()
    return json.loads(row["content"]) if row else None


def verify_in_record(db: sqlite3.Connection, record_id: str, quote: str) -> Citation | None:
    if (c := verify_quote(db, record_id, None, quote)):
        return c
    for p in db.execute("SELECT page_no FROM document_pages WHERE document_id=? ORDER BY page_no", (record_id,)):
        if (c := verify_quote(db, record_id, p["page_no"], quote)):
            return c
    return None


# ------------------------------------------------------------------------------------------------------------------
# F2 — key moments
# ------------------------------------------------------------------------------------------------------------------
class MomentX(BaseModel):
    record_id: str
    title: str = Field(description="<= 8 words naming the moment")
    date: str | None = Field(description="ISO date of the moment if known")
    importance: int = Field(ge=1, le=10)
    rank_reason: str = Field(description="<= 22 words: why this is one of the moments that define the case")
    quote: str = Field(description="Exact words copied from that candidate's text that show the moment")


class MomentsX(BaseModel):
    moments: list[MomentX]


def _candidates(db: sqlite3.Connection, matter_id: int) -> list[sqlite3.Row]:
    return db.execute("""SELECT d.*, r.type, r.title AS rtitle, r.occurred_at, r.body_text FROM digests d
                         JOIN records r ON r.id = d.record_id
                         WHERE d.matter_id=? AND r.deleted_at IS NULL AND d.importance >= ?
                         ORDER BY d.importance DESC, r.occurred_at LIMIT 60""",
                      (matter_id, MOMENT_MIN_IMPORTANCE)).fetchall()


def key_moments(db: sqlite3.Connection, matter_id: int) -> list[dict]:
    cands = _candidates(db, matter_id)
    h = hashlib.sha256((BRIEF_VERSION + "|moments|" + "|".join(f"{c['record_id']}:{c['content_hash']}"
                                                                for c in cands)).encode()).hexdigest()
    if (cached := _cache_get(db, matter_id, "key_moments", h)) is not None:
        log_cache_hit("key_moments", settings.model_main, matter_id=matter_id)
        return cached
    if not cands:
        _cache_put(db, matter_id, "key_moments", h, [])
        return []
    blocks = []
    for c in cands:
        text = c["body_text"][:700]
        if c["type"] == "document":
            pages = db.execute("SELECT page_no, text FROM document_pages WHERE document_id=? AND text!='' "
                               "ORDER BY page_no LIMIT 3", (c["record_id"],)).fetchall()
            text += "\n" + "\n".join(f"[p{p['page_no']}] {p['text'][:500]}" for p in pages)
        blocks.append(f'<candidate record_id="{c["record_id"]}" type="{c["type"]}" date="{c["occurred_at"] or ""}" '
                      f'importance="{c["importance"]}">\nDigest: {c["one_liner"]} — {c["importance_reason"]}\n'
                      f"Text: {text}\n</candidate>")
    ctx = context_block(matter_context(db, matter_id))
    parsed, _ = call_claude_parsed(
        "key_moments", settings.model_main, MomentsX, matter_id=matter_id, max_tokens=8000,
        output_config={"effort": "low"},
        system=("You pick the moments that define a personal-injury case for an attorney who has 90 seconds. "
                "Choose at most 10 from the candidates, most important first; merge duplicates of the same event "
                "(keep the best source). Use only the candidates; the quote must be copied exactly from the chosen "
                "candidate's text."),
        messages=[{"role": "user", "content": f"{ctx}\n\nCandidates:\n" + "\n".join(blocks)}])
    valid = {c["record_id"] for c in cands}
    out = []
    for m in parsed.moments[:10]:
        if m.record_id not in valid:
            continue
        cit = verify_in_record(db, m.record_id, m.quote) or record_citation(db, m.record_id)
        if cit is None:
            continue
        out.append(KeyMoment(rank=len(out) + 1, date=m.date, title=m.title, importance=m.importance,
                             rank_reason=m.rank_reason, citations=[cit]).model_dump(mode="json"))
    _cache_put(db, matter_id, "key_moments", h, out)
    return out


# ------------------------------------------------------------------------------------------------------------------
# Story so far (native citations)
# ------------------------------------------------------------------------------------------------------------------
def _first_chunks(db: sqlite3.Connection, record_ids: list[str], prefer_pages: dict[str, int] | None = None) -> list[Hit]:
    ids = []
    for rid in record_ids:
        page = (prefer_pages or {}).get(rid)
        row = db.execute("SELECT id FROM chunks WHERE record_id=? AND page_no IS ? ORDER BY char_start LIMIT 1",
                         (rid, page)).fetchone() or db.execute(
            "SELECT id FROM chunks WHERE record_id=? ORDER BY page_no, char_start LIMIT 1", (rid,)).fetchone()
        if row:
            ids.append(row["id"])
    hits = hydrate(db, ids)
    return [hits[i] for i in ids if i in hits]


def story(db: sqlite3.Connection, matter_id: int) -> list[dict]:
    top = db.execute("""SELECT d.record_id FROM digests d JOIN records r ON r.id=d.record_id
                        WHERE d.matter_id=? AND r.deleted_at IS NULL ORDER BY d.importance DESC, r.occurred_at DESC
                        LIMIT 18""", (matter_id,)).fetchall()
    rids = [r["record_id"] for r in top]
    pages: dict[str, int] = {}
    for f in db.execute("SELECT citations FROM facts WHERE matter_id=? AND kind IN ('injury','coverage')", (matter_id,)):
        for c in jload(f["citations"], []) or []:
            if c["record_id"] not in rids:
                rids.append(c["record_id"])
            if c.get("page"):
                pages[c["record_id"]] = c["page"]
    hits = _first_chunks(db, rids[:26], pages)
    h = hashlib.sha256((BRIEF_VERSION + "|story|" + "|".join(f"{x.chunk_id}:{x.text[:50]}" for x in hits)).encode()
                       ).hexdigest()
    if (cached := _cache_get(db, matter_id, "story", h)) is not None:
        log_cache_hit("brief", settings.model_main, matter_id=matter_id)
        return cached
    ctx = context_block(matter_context(db, matter_id))
    sentences = cited_generation(
        "brief", matter_id, hits,
        f"{ctx}\n\nWrite the story of this case so far as 5-7 short bullet lines (one line each, chronological): "
        "what happened, the injuries and treatment, insurance/coverage, where the case stands now, and what is "
        "next or blocking. Every line must be supported by the sources above.",
        system="You brief a personal-injury attorney who has 90 seconds. Only state facts found in the sources.")
    out = [s.model_dump(mode="json") for s in sentences]
    _cache_put(db, matter_id, "story", h, out)
    return out


# ------------------------------------------------------------------------------------------------------------------
# F1 — delta summary since a timestamp
# ------------------------------------------------------------------------------------------------------------------
def delta(db: sqlite3.Connection, matter_id: int, since: str | None) -> tuple[list[dict], bool]:
    rows = db.execute("""SELECT r.id, r.content_hash FROM records r LEFT JOIN digests d ON d.record_id=r.id
                         WHERE r.matter_id=? AND r.last_changed_at > ? AND r.type != 'contact'
                         ORDER BY COALESCE(d.importance,0) DESC LIMIT 20""",
                      (matter_id, since or "")).fetchall()
    if not rows:
        return [], True
    h = hashlib.sha256((BRIEF_VERSION + "|delta|" + "|".join(f"{r['id']}:{r['content_hash']}" for r in rows))
                       .encode()).hexdigest()
    if (cached := _cache_get(db, matter_id, "delta", h)) is not None:
        return cached, True
    hits = _first_chunks(db, [r["id"] for r in rows])
    sentences = cited_generation(
        "delta", matter_id, hits,
        f"These items are new or changed since the attorney's last visit ({since or 'first visit'}). Summarize what "
        "changed in 2-4 bullet lines, most consequential first, each grounded in the sources.",
        system="You tell a busy attorney what changed on their case. Only state facts found in the sources.")
    out = [s.model_dump(mode="json") for s in sentences]
    _cache_put(db, matter_id, "delta", h, out)
    return out, False


# ------------------------------------------------------------------------------------------------------------------
class QuestionsX(BaseModel):
    questions: list[str] = Field(description="5 short questions an attorney would ask about THIS case")


def suggested_questions(db: sqlite3.Connection, matter_id: int) -> list[str]:
    top = db.execute("""SELECT one_liner, content_hash FROM digests WHERE matter_id=? ORDER BY importance DESC
                        LIMIT 25""", (matter_id,)).fetchall()
    h = hashlib.sha256((BRIEF_VERSION + "|q|" + "|".join(t["content_hash"] for t in top)).encode()).hexdigest()
    if (cached := _cache_get(db, matter_id, "suggested_questions", h)) is not None:
        return cached
    if not top:
        return []
    parsed, _ = call_claude_parsed(
        "brief", settings.model_fast, QuestionsX, matter_id=matter_id, max_tokens=1000,
        messages=[{"role": "user", "content": "Case highlights:\n" + "\n".join(f"- {t['one_liner']}" for t in top)
                   + "\n\nSuggest 5 short, specific questions an attorney would want answered from this file "
                     "(injuries, coverage, treatment status, deadlines, what we're waiting on)."}])
    out = parsed.questions[:5]
    _cache_put(db, matter_id, "suggested_questions", h, out)
    return out


def ensure_brief(db: sqlite3.Connection, matter_id: int) -> dict:
    out = {}
    for name, fn in (("key_moments", key_moments), ("story", story), ("suggested_questions", suggested_questions)):
        try:
            out[name] = len(fn(db, matter_id))
        except Exception as e:  # noqa: BLE001
            log.warning("brief %s failed: %s", name, e)
            out[name] = f"error: {e}"[:200]
    return out
