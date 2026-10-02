"""Locate/verify a highlighted passage (RAG highlight-to-source) and draft provider-safe status notes (F5)."""
from __future__ import annotations

import sqlite3

from pydantic import BaseModel, Field

from ..config import settings
from ..contracts import Citation, DraftFlag, LocateResult, ProviderDraft
from ..llm import call_claude_parsed
from ..rag.cite import verify_quote
from ..rag.search import hybrid_search
from . import value
from .views import open_requests


class Support(BaseModel):
    candidate: str = Field(description="Candidate id, e.g. C2")
    supports: bool
    quote: str = Field(description="Exact words from the candidate that support the statement ('' if none)")


class SupportX(BaseModel):
    results: list[Support]
    explanation: str = Field(description="One sentence: is the statement supported by the case file?")


def locate(db: sqlite3.Connection, matter_id: int, text: str) -> LocateResult:
    hits = hybrid_search(db, matter_id, text, k=6)
    if not hits:
        return LocateResult(supported=False, citations=[], explanation="No supporting source found in the case file.")
    cands = "\n\n".join(f'<candidate id="C{i}">\n{h.text}\n</candidate>' for i, h in enumerate(hits))
    parsed, _ = call_claude_parsed(
        "locate", settings.model_fast, SupportX, matter_id=matter_id, max_tokens=2000,
        messages=[{"role": "user", "content": (
            f"Statement: \"{text}\"\n\nCandidates from the case file:\n{cands}\n\nFor each candidate, does it directly "
            "support the statement? If yes, copy the exact supporting words.")}])
    cits: list[Citation] = []
    for s in parsed.results:
        if not s.supports or not s.quote.strip():
            continue
        try:
            h = hits[int(s.candidate.strip().lstrip("Cc"))]
        except (ValueError, IndexError):
            continue
        if (c := verify_quote(db, h.record_id, h.page, s.quote)):
            cits.append(c)
    if not cits:
        return LocateResult(supported=False, citations=[],
                            explanation="No supporting source found in the case file for this text.")
    return LocateResult(supported=True, citations=cits, explanation=parsed.explanation)


class DraftX(BaseModel):
    draft: str = Field(description="2-4 plain sentences for the provider's office")


class FlagsX(BaseModel):
    flags: list[DraftFlag]


def provider_draft(db: sqlite3.Connection, matter_id: int, provider_contact_id: int, fields: list[str]) -> ProviderDraft:
    m = db.execute("SELECT * FROM matters WHERE id=?", (matter_id,)).fetchone()
    prov = db.execute("SELECT name FROM contacts WHERE id=?", (provider_contact_id,)).fetchone()
    facts = [f"Case status: {m['status'] or 'unknown'}; stage: {m['stage_name'] or 'unknown'}"]
    safe = db.execute("""SELECT r.occurred_at, d.provider_safe_summary FROM digests d JOIN records r ON r.id=d.record_id
                         WHERE d.matter_id=? AND d.confidential=0 AND d.provider_safe_summary IS NOT NULL
                         ORDER BY r.occurred_at DESC LIMIT 12""", (matter_id,)).fetchall()
    facts += [f"{(s['occurred_at'] or '')[:10]}: {s['provider_safe_summary']}" for s in safe]
    if "open_requests" in fields:
        facts += [f"Requested from this office: {r['description']} (requested {r['requested_at'] or 'recently'})"
                  for r in open_requests(db, matter_id, provider_contact_id)]
    if "coverage" in fields:
        facts.append("Liability coverage confirmed" if value.coverage(db, matter_id).confirmed
                     else "Coverage not yet confirmed")
    draft, _ = call_claude_parsed(
        "draft", settings.model_main, DraftX, matter_id=matter_id, max_tokens=2000, output_config={"effort": "low"},
        system=("You write short, neutral status notes from a personal-injury law firm to a treating medical "
                "provider's office. Share only status and what the firm needs from them. Never mention strategy, "
                "case value, settlement amounts, negotiations, or internal opinions."),
        messages=[{"role": "user", "content": f"Provider: {prov['name'] if prov else 'the provider'}\n"
                                              "Facts you may use:\n- " + "\n- ".join(facts)}])
    flags, _ = call_claude_parsed(
        "classify", settings.model_fast, FlagsX, matter_id=matter_id, max_tokens=1000,
        messages=[{"role": "user", "content": (
            "A law firm will send this note to an outside medical provider. Flag any phrase that reveals case "
            "strategy, valuation, settlement/negotiation details, attorney opinions or other confidential "
            f"information (return an empty list if none).\n\nNote:\n{draft.draft}")}])
    return ProviderDraft(draft=draft.draft, flags=flags.flags)
