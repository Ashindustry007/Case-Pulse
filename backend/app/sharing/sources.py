"""[Dev 2] Read-only adapter over Dev 1's tables: the ONLY sharing module that knows their schema.

Agreed shapes: docs/workstreams/interface-dev1-dev2.md. Every reader returns None / [] when data is missing
(no sync or digest yet, or a malformed fact), so the projection omits that section instead of failing.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from ..config import settings
from ..contracts import (BillLine, Coverage, Movement, NotFound, ProviderBills, ProviderIdentity, SharedDocument,
                         StageShare, WorthEstimate)
from ..db import jload


def data_dir() -> Path:
    """Root that records.meta.file_path is relative to (patched in tests)."""
    return settings.data_dir


def matter(db: sqlite3.Connection, matter_id: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM matters WHERE id = ?", (matter_id,)).fetchone()


def patient_display(db: sqlite3.Connection, matter_id: int) -> str:
    """Client initials ("J. R."); the full name never leaves the server."""
    row = db.execute("SELECT c.name FROM matters m JOIN contacts c ON c.id = m.client_id WHERE m.id = ?",
                     (matter_id,)).fetchone()
    parts = (row["name"] or "").replace(",", " ").split() if row else []
    return " ".join(f"{p[0].upper()}." for p in parts[:2]) or "Patient"


def stage(db: sqlite3.Connection, matter_id: int) -> StageShare | None:
    m = matter(db, matter_id)
    if m is None or not m["stage_name"]:
        return None
    names = [r["name"] for r in db.execute(
        "SELECT name FROM matter_stages WHERE ? IS NULL OR practice_area IS ? ORDER BY sort_order, id",
        (m["practice_area"], m["practice_area"]))]
    return StageShare(current=m["stage_name"], stages=names,
                      index=names.index(m["stage_name"]) if m["stage_name"] in names else None)


def last_activity_at(db: sqlite3.Connection, matter_id: int, until: str) -> str | None:
    """Most recent past record date (future due dates don't count as activity)."""
    return db.execute("SELECT MAX(occurred_at) AS at FROM records WHERE matter_id = ? AND deleted_at IS NULL "
                      "AND occurred_at IS NOT NULL AND occurred_at <= ?", (matter_id, until)).fetchone()["at"]


def movements(db: sqlite3.Connection, matter_id: int, until: str, limit: int = 5) -> list[Movement]:
    rows = db.execute(
        "SELECT r.occurred_at, d.provider_safe_summary AS text FROM records r JOIN digests d ON d.record_id = r.id "
        "WHERE r.matter_id = ? AND r.deleted_at IS NULL AND r.occurred_at IS NOT NULL AND r.occurred_at <= ? "
        "AND d.confidential = 0 AND COALESCE(d.provider_safe_summary, '') != '' "
        "ORDER BY r.occurred_at DESC LIMIT ?", (matter_id, until, limit))
    return [Movement(date=r["occurred_at"][:10], text=r["text"]) for r in rows]


def provider_identity(db: sqlite3.Connection, contact_id: int) -> ProviderIdentity | None:
    row = db.execute("SELECT id, name, email FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    return ProviderIdentity(contact_id=row["id"], name=row["name"] or "Provider", email=row["email"]) if row else None


def provider_bills(db: sqlite3.Connection, matter_id: int, contact_id: int) -> ProviderBills | None:
    rows = db.execute("SELECT title, occurred_at, meta FROM records WHERE matter_id = ? AND type = 'medical_bill' "
                      "AND deleted_at IS NULL AND json_extract(meta, '$.provider_contact_id') = ? ORDER BY occurred_at",
                      (matter_id, contact_id)).fetchall()
    if not rows:
        return None
    metas = [jload(r["meta"], {}) for r in rows]
    balances = [float(m["balance"]) for m in metas if m.get("balance") is not None]
    return ProviderBills(
        billed=sum(float(m.get("amount") or 0) for m in metas),
        balance=sum(balances) if balances else None,
        lien=any(bool(m.get("lien")) for m in metas),
        items=[BillLine(date=(r["occurred_at"] or "")[:10] or None, amount=float(m.get("amount") or 0),
                        description=m.get("description") or r["title"]) for r, m in zip(rows, metas)])


def documents(db: sqlite3.Connection, matter_id: int) -> list[SharedDocument]:
    rows = db.execute("SELECT r.id, r.title, (SELECT COUNT(*) FROM document_pages p WHERE p.document_id = r.id) AS pages "
                      "FROM records r WHERE r.matter_id = ? AND r.type = 'document' AND r.deleted_at IS NULL "
                      "ORDER BY r.occurred_at DESC, r.id", (matter_id,))
    return [SharedDocument(id=r["id"], title=r["title"] or "Document", page_count=r["pages"] or None) for r in rows]


def document_path(db: sqlite3.Connection, matter_id: int, document_id: str) -> Path | None:
    row = db.execute("SELECT meta FROM records WHERE id = ? AND matter_id = ? AND type = 'document' "
                     "AND deleted_at IS NULL", (document_id, matter_id)).fetchone()
    rel = jload(row["meta"], {}).get("file_path") if row else None
    if not rel:
        return None
    root = data_dir().resolve()
    path = (root / rel).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def provider_request_rows(db: sqlite3.Connection, matter_id: int, contact_id: int) -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM provider_requests WHERE matter_id = ? AND provider_contact_id = ? "
                      "ORDER BY requested_at DESC, id", (matter_id, contact_id)).fetchall()


def provider_request(db: sqlite3.Connection, request_id: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM provider_requests WHERE id = ?", (request_id,)).fetchone()


def _latest_fact(db: sqlite3.Connection, matter_id: int, kind: str):
    row = db.execute("SELECT value FROM facts WHERE matter_id = ? AND kind = ? ORDER BY created_at DESC, id DESC "
                     "LIMIT 1", (matter_id, kind)).fetchone()
    return jload(row["value"]) if row else None


def coverage(db: sqlite3.Connection, matter_id: int) -> Coverage | None:
    raw = _latest_fact(db, matter_id, "coverage")
    if raw is None:
        return None
    try:
        return Coverage.model_validate(raw)
    except ValidationError as e:
        print(f"[sharing] ignoring malformed coverage fact for matter {matter_id}: {e.error_count()} errors")
        return None


_WORTH = TypeAdapter(WorthEstimate | NotFound)


def worth(db: sqlite3.Connection, matter_id: int) -> WorthEstimate | None:
    raw = _latest_fact(db, matter_id, "worth")
    if raw is None:
        return None
    try:
        parsed = _WORTH.validate_python(raw)
    except ValidationError as e:
        print(f"[sharing] ignoring malformed worth fact for matter {matter_id}: {e.error_count()} errors")
        return None
    return parsed if isinstance(parsed, WorthEstimate) else None


def treatment_visits(db: sqlite3.Connection, matter_id: int) -> list[dict]:
    rows = db.execute("SELECT value FROM facts WHERE matter_id = ? AND kind = 'treatment_visit'", (matter_id,))
    return [v for v in (jload(r["value"], {}) for r in rows) if isinstance(v, dict) and v.get("date")]
