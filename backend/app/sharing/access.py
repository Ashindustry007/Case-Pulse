"""[Dev 2] Provider-side access: ownership filter on every query. Anything not theirs → 404 (never 403),
so grant ids can't be probed."""
from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from ..contracts import ProviderCase, ProviderCaseSummary, SharePolicy
from . import grants, projection


def owned_grant(db: sqlite3.Connection, grant_id: int, user: sqlite3.Row) -> tuple[sqlite3.Row, SharePolicy]:
    grant = db.execute("SELECT * FROM share_grants WHERE id = ? AND provider_user_id = ? AND revoked_at IS NULL",
                       (grant_id, user["id"])).fetchone()
    policy = grants.latest_policy(db, grant_id) if grant else None
    if grant is None or policy is None:
        raise HTTPException(404, "Case not found")
    return grant, policy


def case_for(db: sqlite3.Connection, grant: sqlite3.Row, policy: SharePolicy) -> ProviderCase:
    sections = projection.build_sections(db, grant["matter_id"], grant["provider_contact_id"])
    return projection.project(sections, grant_id=grant["id"], policy=policy, shared_by=policy.released_by)


def summaries(db: sqlite3.Connection, user: sqlite3.Row) -> list[ProviderCaseSummary]:
    out = []
    for g in db.execute("SELECT * FROM share_grants WHERE provider_user_id = ? AND revoked_at IS NULL ORDER BY id DESC",
                        (user["id"],)).fetchall():
        policy = grants.latest_policy(db, g["id"])
        if policy is None:
            continue
        case = case_for(db, g, policy)          # derive from the projection so the whitelist applies here too
        hb = case.heartbeat
        out.append(ProviderCaseSummary(
            grant_id=g["id"], patient_display=case.patient_display, firm_name=case.firm_name,
            state=hb.state if hb else None, last_movement_at=hb.last_movement.date if hb and hb.last_movement else None,
            open_requests=sum(1 for r in case.requests or [] if r.state == "open")))
    return out
