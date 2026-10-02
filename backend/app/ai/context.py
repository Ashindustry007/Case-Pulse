"""Shared, case-agnostic context helpers for prompts (who is the client, who is internal staff, providers...)."""
from __future__ import annotations

import sqlite3

from ..db import jload


def matter_context(db: sqlite3.Connection, matter_id: int) -> dict:
    m = db.execute("SELECT * FROM matters WHERE id=?", (matter_id,)).fetchone()
    client = db.execute("""SELECT c.id, c.name FROM matter_contacts mc JOIN contacts c ON c.id=mc.contact_id
                           WHERE mc.matter_id=? AND mc.is_client=1 LIMIT 1""", (matter_id,)).fetchone()
    staff = [r["name"] for r in db.execute("SELECT name FROM firm_users WHERE name IS NOT NULL")]
    parties = [dict(r) for r in db.execute(
        """SELECT c.id, c.name, mc.relationship, mc.role FROM matter_contacts mc JOIN contacts c ON c.id=mc.contact_id
           WHERE mc.matter_id=?""", (matter_id,))]
    return {
        "matter": (m["description"] if m else None) or (m["display_number"] if m else ""),
        "stage": m["stage_name"] if m else None,
        "status": m["status"] if m else None,
        "client": client["name"] if client else None,
        "client_id": client["id"] if client else None,
        "staff": staff,
        "parties": parties,
    }


def context_block(ctx: dict) -> str:
    parties = "\n".join(f"- {p['name']} ({p['relationship'] or p['role']})" for p in ctx["parties"]) or "- (none)"
    staff = ", ".join(ctx["staff"]) or "(unknown)"
    return (f"Matter: {ctx['matter']}\nCurrent stage: {ctx['stage'] or 'unknown'} · status: {ctx['status'] or 'unknown'}\n"
            f"Client: {ctx['client'] or 'unknown'}\nFirm staff (internal): {staff}\nOther parties:\n{parties}")


def record_meta(row: sqlite3.Row) -> dict:
    return jload(row["meta"], {}) or {}
