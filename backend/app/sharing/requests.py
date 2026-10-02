"""[Dev 2] Provider request view + app-local state (F7). State lives in request_states; never Clio."""
from __future__ import annotations

import sqlite3
from typing import Literal

from ..contracts import ProviderRequest
from ..db import jload, now_iso
from . import sources


def requests_for(db: sqlite3.Connection, matter_id: int, provider_contact_id: int, *,
                 audience: Literal["attorney", "provider"]) -> list[ProviderRequest]:
    rows = sources.provider_request_rows(db, matter_id, provider_contact_id)
    if not rows:
        return []
    marks = ",".join("?" * len(rows))
    states = {r["request_id"]: r["state"] for r in db.execute(
        f"SELECT request_id, state FROM request_states WHERE request_id IN ({marks})", [r["id"] for r in rows])}
    return [ProviderRequest(
        id=r["id"], kind=r["kind"], description=r["description"],
        requested_at=(r["requested_at"] or "")[:10] or None, channel=r["channel"],
        state=states.get(r["id"], "open"), provider_contact_id=r["provider_contact_id"],
        # Attorneys always see the source; providers only when the source message was addressed to them.
        citations=jload(r["citations"], []) if audience == "attorney" or r["source_addressed_to_provider"] else [],
    ) for r in rows]


def set_state(db: sqlite3.Connection, request_id: str, state: str, user_id: int) -> None:
    db.execute("INSERT INTO request_states(request_id, state, by_user_id, at) VALUES (?,?,?,?) "
               "ON CONFLICT(request_id) DO UPDATE SET state = excluded.state, by_user_id = excluded.by_user_id, "
               "at = excluded.at", (request_id, state, user_id, now_iso()))
