"""Auth + role guards (shared, FROZEN; Dev 2 owns hardening).

- Session: signed JWT (HS256) in httpOnly cookie `cp_session` with {sub, role}. The user row is re-loaded on every request,
  so deleting/changing a user takes effect immediately.
- Every route MUST declare exactly one guard: `Depends(require_role("attorney"))`, `Depends(require_role("provider"))`,
  or `Depends(public)`. `main.py` refuses to start if any API route has none (deny-by-default).

CLI:  python -m backend.app.auth seed-attorney      (reads ATTORNEY_EMAIL / ATTORNEY_PASSWORD / ATTORNEY_NAME)
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response, status

from .config import settings
from .contracts import UserOut
from .db import connect, get_db, now_iso

COOKIE_NAME = "cp_session"
SESSION_HOURS = 8
_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def issue_session(response: Response, user_id: int, role: str) -> None:
    exp = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    token = jwt.encode({"sub": str(user_id), "role": role, "exp": exp}, settings.jwt_secret, algorithm="HS256")
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=False,
                        max_age=SESSION_HOURS * 3600, path="/")


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def user_out(row: sqlite3.Row) -> UserOut:
    return UserOut(id=row["id"], email=row["email"], name=row["name"], role=row["role"],
                   provider_contact_id=row["provider_contact_id"])


def _token_from_request(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):  # convenience for scripts/smoke tests
        return auth[7:]
    return None


def current_user_optional(request: Request, db: sqlite3.Connection = Depends(get_db)) -> sqlite3.Row | None:
    token = _token_from_request(request)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    return db.execute("SELECT * FROM users WHERE id = ?", (int(payload["sub"]),)).fetchone()


def current_user(user: sqlite3.Row | None = Depends(current_user_optional)) -> sqlite3.Row:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


def require_role(*roles: str):
    """Route guard. Usage: APIRouter(dependencies=[Depends(require_role("attorney"))])."""

    def _guard(user: sqlite3.Row = Depends(current_user)) -> sqlite3.Row:
        if user["role"] not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed for this role")
        return user

    _guard.__role_guard__ = roles  # type: ignore[attr-defined]
    return _guard


def public() -> None:
    """Explicit marker for routes that need no session (login, invite accept, OAuth callback)."""


public.__role_guard__ = ("public",)  # type: ignore[attr-defined]


def create_user(db: sqlite3.Connection, email: str, password: str, name: str | None, role: str,
                provider_contact_id: int | None = None) -> int:
    existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        db.execute("UPDATE users SET password_hash=?, name=COALESCE(?, name), role=?, provider_contact_id=? WHERE id=?",
                   (hash_password(password), name, role, provider_contact_id, existing["id"]))
        return existing["id"]
    cur = db.execute(
        "INSERT INTO users(email, password_hash, name, role, provider_contact_id, created_at) VALUES (?,?,?,?,?,?)",
        (email, hash_password(password), name, role, provider_contact_id, now_iso()))
    return int(cur.lastrowid)


def seed_attorney() -> None:
    if not settings.attorney_password:
        sys.exit("Set ATTORNEY_PASSWORD (and ATTORNEY_EMAIL) in .env first")
    with connect() as db:
        uid = create_user(db, settings.attorney_email, settings.attorney_password, settings.attorney_name, "attorney")
    print(f"attorney user ready: {settings.attorney_email} (id {uid})")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "seed-attorney":
        seed_attorney()
    else:
        print(__doc__)
