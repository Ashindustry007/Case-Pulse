"""[Dev 1] Clio connection (OAuth) + sync endpoints. Clio is read-only input."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from ..auth import public, require_role
from ..clio import client as clio
from ..config import settings
from ..contracts import SyncResult, SyncStatus
from ..db import get_db
from ..sync.engine import last_synced_at, sync_matter

router = APIRouter(tags=["sync"])
attorney = require_role("attorney")


@router.get("/auth/clio/login", summary="Redirect the attorney to Clio to authorize read access")
def clio_login(user=Depends(attorney)):
    if not settings.clio_client_id:
        raise HTTPException(500, "CLIO_CLIENT_ID is not configured in .env")
    state = jwt.encode({"uid": user["id"], "exp": datetime.now(timezone.utc) + timedelta(minutes=10)},
                       settings.jwt_secret, algorithm="HS256")
    return RedirectResponse(clio.authorize_url(state))


@router.get("/auth/clio/callback", dependencies=[Depends(public)], summary="Clio OAuth redirect target")
def clio_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code or not state:
        return RedirectResponse(f"{settings.frontend_url}/matters?clio=error")
    try:
        jwt.decode(state, settings.jwt_secret, algorithms=["HS256"])  # CSRF: state must be ours and fresh
    except jwt.PyJWTError:
        raise HTTPException(400, "Invalid OAuth state")
    clio.exchange_code(code)
    return RedirectResponse(f"{settings.frontend_url}/matters?clio=connected")


@router.post("/api/sync/{matter_id}", dependencies=[Depends(attorney)], response_model=SyncResult)
def run_sync(matter_id: int, full: bool = False):
    try:
        res = sync_matter(matter_id, full=True if full else None)
    except clio.ClioNotConnected as e:
        raise HTTPException(409, str(e))
    return SyncResult(matter_id=matter_id, started_at=res["started_at"], finished_at=res["finished_at"],
                      counts=res["counts"], new=res["new"], changed=res["changed"], removed=res["removed"])


@router.get("/api/sync/status", dependencies=[Depends(attorney)], response_model=SyncStatus)
def sync_status(db: sqlite3.Connection = Depends(get_db)):
    st = clio.connection_status()
    n = db.execute("SELECT COUNT(*) FROM matters").fetchone()[0]
    return SyncStatus(connected=st["connected"], clio_user=st["clio_user"], last_synced_at=last_synced_at(db),
                      matters=n)
