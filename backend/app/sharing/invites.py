"""[Dev 2] Provider invites: sha256-hashed single-use codes, 7-day expiry. Delivered via Resend if configured,
and ALWAYS printed to the server console (demo fallback)."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException

from ..auth import create_user, verify_password
from ..config import settings
from ..db import now_iso
from . import events

INVITE_DAYS = 7


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def create_invite(db: sqlite3.Connection, email: str, grant_id: int) -> str:
    code = secrets.token_urlsafe(24)
    expires = (datetime.now(timezone.utc) + timedelta(days=INVITE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.execute("INSERT INTO invites(code_hash, email, grant_id, expires_at, created_at) VALUES (?,?,?,?,?)",
               (_hash(code), email, grant_id, expires, now_iso()))
    return code


def invite_url(code: str) -> str:
    return f"{settings.frontend_url}/invite/{code}"


def deliver(email: str, url: str) -> None:
    print(f"[invite] {email} → {url}", flush=True)
    if not (settings.resend_api_key and settings.invite_from_email):
        return
    try:
        httpx.post("https://api.resend.com/emails", timeout=10,
                   headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                   json={"from": settings.invite_from_email, "to": [email],
                         "subject": f"{settings.firm_name} shared a case update with you",
                         "html": f'<p>{settings.firm_name} shared a case with you on Case Pulse.</p>'
                                 f'<p><a href="{url}">Set your password and view the case</a> (link valid {INVITE_DAYS} days).</p>'}
                   ).raise_for_status()
    except httpx.HTTPError as e:
        print(f"[invite] email delivery failed ({e}); use the console link above", flush=True)


def accept(db: sqlite3.Connection, code: str, password: str, name: str | None) -> sqlite3.Row:
    inv = db.execute("SELECT * FROM invites WHERE code_hash = ?", (_hash(code),)).fetchone()
    if inv is None:
        raise HTTPException(404, "Invite not found")
    if inv["used_at"]:
        raise HTTPException(410, "This invite was already used. Sign in instead.")
    if inv["expires_at"] < now_iso():
        raise HTTPException(410, "This invite has expired. Ask the firm for a new link.")
    grant = db.execute("SELECT * FROM share_grants WHERE id = ?", (inv["grant_id"],)).fetchone()
    if grant is None or grant["revoked_at"]:
        raise HTTPException(410, "This share is no longer active.")
    existing = db.execute("SELECT id, role, password_hash FROM users WHERE email = ?", (inv["email"],)).fetchone()
    if existing and existing["role"] != "provider":
        raise HTTPException(409, "This email belongs to a firm account.")
    if existing:
        if not verify_password(existing["password_hash"], password):
            raise HTTPException(401, "An account already exists for this email. Enter your existing password.")
        uid = existing["id"]
    else:
        uid = create_user(db, inv["email"], password, name, "provider", grant["provider_contact_id"])
    db.execute("UPDATE share_grants SET provider_user_id = ? WHERE id = ?", (uid, grant["id"]))
    db.execute("UPDATE invites SET used_at = ? WHERE code_hash = ?", (now_iso(), inv["code_hash"]))
    user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    latest = db.execute("SELECT MAX(version) AS v FROM share_policies WHERE grant_id = ?", (grant["id"],)).fetchone()
    events.log_event(db, grant["id"], "invite_accepted", user, version=latest["v"])
    return user
