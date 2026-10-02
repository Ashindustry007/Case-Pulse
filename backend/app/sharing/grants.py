"""[Dev 2] Share grants + versioned policies: create, release (→ invite), revoke, audit, candidates (F5, F8)."""
from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from ..contracts import (CreateGrantRequest, Grant, PolicyVersionDiff, ReleaseRequest, ReleaseResult, ShareAudit,
                         ShareCandidates, SharePolicy)
from ..db import jdump, jload, now_iso
from . import events, invites, projection, sources

_POLICY_SQL = ("SELECT p.*, COALESCE(u.name, u.email) AS released_by_name FROM share_policies p "
               "LEFT JOIN users u ON u.id = p.released_by WHERE p.grant_id = ?")


def get_grant(db: sqlite3.Connection, grant_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM share_grants WHERE id = ?", (grant_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Share not found")
    return row


def _policy(row: sqlite3.Row) -> SharePolicy:
    return SharePolicy(grant_id=row["grant_id"], version=row["version"], fields=jload(row["fields"], []),
                       document_ids=jload(row["document_ids"], []), coverage_detail=row["coverage_detail"],
                       status_note=row["status_note"], released_by=row["released_by_name"],
                       released_at=row["released_at"])


def policies(db: sqlite3.Connection, grant_id: int) -> list[SharePolicy]:
    return [_policy(r) for r in db.execute(_POLICY_SQL + " ORDER BY p.version", (grant_id,))]


def latest_policy(db: sqlite3.Connection, grant_id: int) -> SharePolicy | None:
    row = db.execute(_POLICY_SQL + " ORDER BY p.version DESC LIMIT 1", (grant_id,)).fetchone()
    return _policy(row) if row else None


def grant_out(db: sqlite3.Connection, row: sqlite3.Row) -> Grant:
    latest = latest_policy(db, row["id"])
    views = db.execute("SELECT COUNT(*) AS n, MAX(at) AS last FROM share_events WHERE grant_id = ? AND event = 'viewed'",
                       (row["id"],)).fetchone()
    return Grant(id=row["id"], matter_id=row["matter_id"], provider_contact_id=row["provider_contact_id"],
                 provider_name=row["provider_name"], email=row["email"], provider_user_id=row["provider_user_id"],
                 latest_version=latest.version if latest else None,
                 released_at=latest.released_at if latest else None, revoked_at=row["revoked_at"],
                 last_viewed_at=views["last"], view_count=views["n"])


def list_grants(db: sqlite3.Connection, matter_id: int) -> list[Grant]:
    return [grant_out(db, r) for r in db.execute("SELECT * FROM share_grants WHERE matter_id = ? ORDER BY id",
                                                 (matter_id,))]


def _active_grant(db: sqlite3.Connection, matter_id: int, contact_id: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM share_grants WHERE matter_id = ? AND provider_contact_id = ? "
                      "AND revoked_at IS NULL ORDER BY id DESC LIMIT 1", (matter_id, contact_id)).fetchone()


def create_grant(db: sqlite3.Connection, body: CreateGrantRequest, user: sqlite3.Row) -> Grant:
    """Idempotent per (matter, provider): returns the active grant if one exists."""
    row = _active_grant(db, body.matter_id, body.provider_contact_id)
    if row is None:
        ident = sources.provider_identity(db, body.provider_contact_id)
        cur = db.execute("INSERT INTO share_grants(matter_id, provider_contact_id, provider_name, email, created_by, "
                         "created_at) VALUES (?,?,?,?,?,?)",
                         (body.matter_id, body.provider_contact_id, ident.name if ident else None,
                          body.email.strip().lower(), user["id"], now_iso()))
        row = get_grant(db, int(cur.lastrowid))
    return grant_out(db, row)


def release(db: sqlite3.Connection, grant_id: int, body: ReleaseRequest, user: sqlite3.Row) -> ReleaseResult:
    grant = get_grant(db, grant_id)
    if grant["revoked_at"]:
        raise HTTPException(409, "This share was revoked; create a new one")
    unknown = set(body.document_ids) - {d.id for d in sources.documents(db, grant["matter_id"])}
    if unknown:
        raise HTTPException(400, f"Not documents of this matter: {sorted(unknown)}")
    fields, docs = list(dict.fromkeys(body.fields)), list(dict.fromkeys(body.document_ids))
    version = db.execute("SELECT COALESCE(MAX(version), 0) + 1 AS v FROM share_policies WHERE grant_id = ?",
                         (grant_id,)).fetchone()["v"]
    db.execute("INSERT INTO share_policies(grant_id, version, fields, document_ids, coverage_detail, status_note, "
               "released_by, released_at) VALUES (?,?,?,?,?,?,?,?)",
               (grant_id, version, jdump(fields), jdump(docs), body.coverage_detail,
                (body.status_note or "").strip() or None, user["id"], now_iso()))
    events.log_event(db, grant_id, "released", user, version=version, meta={"fields": fields, "document_ids": docs})
    invite_url = None
    if grant["provider_user_id"] is None:
        existing = db.execute("SELECT id FROM users WHERE email = ? AND role = 'provider'",
                              (grant["email"],)).fetchone()
        if existing:   # provider already has an account (e.g. from another matter): attach, no invite needed
            db.execute("UPDATE share_grants SET provider_user_id = ? WHERE id = ?", (existing["id"], grant_id))
        else:
            invite_url = invites.invite_url(invites.create_invite(db, grant["email"], grant_id))
            invites.deliver(grant["email"], invite_url)
            events.log_event(db, grant_id, "invite_sent", user, version=version, meta={"email": grant["email"]})
    return ReleaseResult(policy=latest_policy(db, grant_id), invite_url=invite_url)


def revoke(db: sqlite3.Connection, grant_id: int, user: sqlite3.Row) -> None:
    grant = get_grant(db, grant_id)
    if grant["revoked_at"] is None:
        db.execute("UPDATE share_grants SET revoked_at = ? WHERE id = ?", (now_iso(), grant_id))
        latest = latest_policy(db, grant_id)
        events.log_event(db, grant_id, "revoked", user, version=latest.version if latest else None)


def _diff_keys(p: SharePolicy) -> set[str]:
    keys = set(p.fields) | set(p.document_ids)
    if "coverage" in p.fields:
        keys.add(f"coverage:{p.coverage_detail}")
    return keys


def audit(db: sqlite3.Connection, grant_id: int) -> ShareAudit:
    grant = get_grant(db, grant_id)
    versions, prev = [], set()
    for p in policies(db, grant_id):
        keys = _diff_keys(p)
        versions.append(PolicyVersionDiff(policy=p, added=sorted(keys - prev), removed=sorted(prev - keys)))
        prev = keys
    return ShareAudit(grant=grant_out(db, grant), versions=versions, events=events.events_for(db, grant_id))


def candidates(db: sqlite3.Connection, matter_id: int, provider_contact_id: int) -> ShareCandidates:
    ident = sources.provider_identity(db, provider_contact_id)
    if ident is None:
        raise HTTPException(404, "Provider not found")
    s = projection.build_sections(db, matter_id, provider_contact_id)
    active = _active_grant(db, matter_id, provider_contact_id)
    grant_id = active["id"] if active else 0
    case = projection.project(s, grant_id=grant_id, policy=projection.preview_policy(grant_id, s.documents),
                              shared_by=None)
    return ShareCandidates(provider=ident, case=case, coverage_variants=s.coverage_variants,
                           available_documents=s.documents)
