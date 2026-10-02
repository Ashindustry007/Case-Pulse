"""[Dev 2] Append-only share audit log (F8)."""
from __future__ import annotations

import sqlite3

from ..contracts import ShareEvent
from ..db import jdump, jload, now_iso


def log_event(db: sqlite3.Connection, grant_id: int, event: str, actor: sqlite3.Row | None, *,
              version: int | None = None, meta: dict | None = None) -> None:
    db.execute("INSERT INTO share_events(grant_id, policy_version, event, actor_user_id, actor_email, at, meta) "
               "VALUES (?,?,?,?,?,?,?)",
               (grant_id, version, event, actor["id"] if actor else None, actor["email"] if actor else None,
                now_iso(), jdump(meta or {})))


def events_for(db: sqlite3.Connection, grant_id: int) -> list[ShareEvent]:
    rows = db.execute("SELECT * FROM share_events WHERE grant_id = ? ORDER BY at, id", (grant_id,))
    return [ShareEvent(id=r["id"], grant_id=r["grant_id"], policy_version=r["policy_version"], event=r["event"],
                       actor_email=r["actor_email"], at=r["at"], meta=jload(r["meta"], {})) for r in rows]
