"""Per-record digests (Claude Haiku, batched, structured output). Hash-cached: a record is digested once per content.

Each digest feeds: timeline one-liners, F1 "why it matters", F2 key-moment candidates, waiting-on, last client
contact, confidentiality (never shown to providers) and the provider-safe "last movement" text (F6).
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Literal

from pydantic import BaseModel, Field

from ..config import settings
from ..db import now_iso
from ..llm import call_claude_parsed, log_cache_hit, price_of
from .context import context_block, matter_context

log = logging.getLogger("casepulse.digest")
DIGEST_VERSION = "d1"
BATCH = 12
MAX_ITEM_CHARS = 5000
SKIP_TYPES = ("contact",)  # contact cards are reference data, not events

Category = Literal["liability", "injury_medical", "treatment", "billing_liens", "coverage_insurance", "negotiation",
                   "litigation", "client_communication", "deadline", "admin", "other"]


class ItemDigest(BaseModel):
    record_id: str
    one_liner: str = Field(description="<= 14 words, plain language, what this item is/says")
    category: Category
    importance: int = Field(ge=1, le=10)
    importance_reason: str = Field(description="<= 20 words: why this importance score")
    why_it_matters: str = Field(description="<= 18 words for a busy attorney: the consequence for the case")
    client_contact: bool = Field(description="True only if this item records an actual exchange WITH the client")
    waiting_on: str | None = Field(description="If the firm is waiting on someone: '<who>: <what>'; else null")
    confidential: bool = Field(description="True for strategy, valuation, settlement posture, internal opinions")
    provider_safe_summary: str | None = Field(
        description="<= 15 words a treating medical provider may see (status/records/bills/appointments), "
                    "or null if confidential or irrelevant to providers")


class DigestBatch(BaseModel):
    items: list[ItemDigest]


SYSTEM = """You digest entries from a personal-injury law firm's case file so attorneys can find what matters fast.
For EACH item return one digest. Be literal and grounded: use only what the item says.

Importance rubric (generic personal-injury practice):
10 the incident itself; liability admitted/denied; policy limits disclosed or tendered; settlement/verdict; suit filed; surgery performed
8-9 objective diagnosis (imaging findings, fractures, herniations); surgery recommended; coverage confirmed/denied; demand sent; offer received; IME; deposition; court deadlines; treatment gaps or the client stopping treatment
5-7 treatment milestones; records/bills received; substantive client updates; liens asserted; experts retained; significant expenses
2-4 routine scheduling, follow-ups, records requests, administrative notes
1 trivial or duplicate

confidential = true for internal strategy, case valuation, settlement posture/authority, attorney opinions, credibility
concerns, or anything a lawyer would not share with an outside medical provider.
provider_safe_summary: only neutral status facts a treating doctor's office may see; never amounts offered/demanded,
strategy, or opinions. null if confidential or not relevant to a medical provider."""


def digest_input_hash(row: sqlite3.Row, pages_hash: str) -> str:
    return hashlib.sha256(f"{DIGEST_VERSION}|{row['content_hash']}|{pages_hash}".encode()).hexdigest()


def _item_text(db: sqlite3.Connection, row: sqlite3.Row) -> tuple[str, str]:
    text = row["body_text"] or ""
    pages_hash = ""
    if row["type"] == "document":
        pages = db.execute("SELECT page_no, text, text_hash FROM document_pages WHERE document_id=? ORDER BY page_no",
                           (row["id"],)).fetchall()
        pages_hash = hashlib.sha256("|".join(p["text_hash"] or "" for p in pages).encode()).hexdigest()
        body = "\n".join(f"[page {p['page_no']}] {p['text']}" for p in pages if p["text"])
        text = f"{text}\nPages: {len(pages)}\n{body}"
    if len(text) > MAX_ITEM_CHARS:
        text = text[:MAX_ITEM_CHARS] + "\n[…truncated]"
    return text, pages_hash


def _run_batch(matter_id: int, ctx_text: str, batch: list[tuple[sqlite3.Row, str, str]]) -> tuple[list[ItemDigest], float, str]:
    items = "\n\n".join(f"<item record_id=\"{r['id']}\" type=\"{r['type']}\" date=\"{r['occurred_at'] or ''}\">\n{t}\n</item>"
                        for r, t, _ in batch)
    parsed, msg = call_claude_parsed(
        "digest", settings.model_fast, DigestBatch, matter_id=matter_id, max_tokens=8000,
        system=SYSTEM, messages=[{"role": "user", "content": f"{ctx_text}\n\nItems:\n{items}"}])
    return parsed.items, price_of(getattr(msg, "model", settings.model_fast), msg.usage), getattr(msg, "model", "")


def digest_matter(db: sqlite3.Connection, matter_id: int, workers: int = 4) -> dict:
    rows = db.execute(f"""SELECT * FROM records WHERE matter_id=? AND deleted_at IS NULL
                          AND type NOT IN ({','.join('?' * len(SKIP_TYPES))})""",
                      (matter_id, *SKIP_TYPES)).fetchall()
    todo: list[tuple[sqlite3.Row, str, str]] = []
    saved = 0.0
    skipped = 0
    for r in rows:
        text, pages_hash = _item_text(db, r)
        h = digest_input_hash(r, pages_hash)
        prev = db.execute("SELECT content_hash, cost_usd FROM digests WHERE record_id=?", (r["id"],)).fetchone()
        if prev and prev["content_hash"] == h:
            skipped += 1
            saved += prev["cost_usd"] or 0
            continue
        todo.append((r, text, h))
    if skipped:
        log_cache_hit("digest", settings.model_fast, matter_id=matter_id, saved_usd=saved)
    stats = {"records": len(rows), "skipped": skipped, "digested": 0, "errors": 0}
    if not todo:
        return stats
    ctx_text = context_block(matter_context(db, matter_id))
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_run_batch, matter_id, ctx_text, b): b for b in batches}
        for fut in as_completed(futs):
            batch = futs[fut]
            try:
                items, cost, model = fut.result()
            except Exception as e:  # noqa: BLE001
                log.warning("digest batch failed: %s", e)
                stats["errors"] += len(batch)
                continue
            by_id = {i.record_id: i for i in items}
            total_chars = sum(len(t) for _, t, _ in batch) or 1
            for r, text, h in batch:
                d = by_id.get(r["id"])
                if d is None:
                    stats["errors"] += 1
                    continue
                share = cost * len(text) / total_chars
                db.execute(
                    """INSERT INTO digests(record_id, matter_id, content_hash, one_liner, category, importance,
                         importance_reason, why_it_matters, client_contact, waiting_on, confidential,
                         provider_safe_summary, model, input_tokens, output_tokens, cost_usd, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(record_id) DO UPDATE SET content_hash=excluded.content_hash,
                         one_liner=excluded.one_liner, category=excluded.category, importance=excluded.importance,
                         importance_reason=excluded.importance_reason, why_it_matters=excluded.why_it_matters,
                         client_contact=excluded.client_contact, waiting_on=excluded.waiting_on,
                         confidential=excluded.confidential, provider_safe_summary=excluded.provider_safe_summary,
                         model=excluded.model, cost_usd=excluded.cost_usd, created_at=excluded.created_at""",
                    (r["id"], matter_id, h, d.one_liner, d.category, d.importance, d.importance_reason,
                     d.why_it_matters, int(d.client_contact), d.waiting_on, int(d.confidential),
                     None if d.confidential else d.provider_safe_summary, model, 0, 0, round(share, 6), now_iso()))
                stats["digested"] += 1
            db.commit()
    return stats
