"""[Dev 2] Share grants, versioned policies, candidates, audit, attorney request actions (F5, F7, F8)."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_user, require_role
from ..contracts import (CreateGrantRequest, Grant, OkResponse, ProviderRequest, ReleaseRequest, ReleaseResult,
                         ShareAudit, ShareCandidates)
from ..db import get_db
from ..sharing import events, grants, requests, sources

router = APIRouter(prefix="/api", tags=["shares"], dependencies=[Depends(require_role("attorney"))])


@router.get("/matters/{matter_id}/share-candidates", response_model=ShareCandidates,
            response_model_exclude_none=True)
def share_candidates(matter_id: int, provider_contact_id: int, db: sqlite3.Connection = Depends(get_db)):
    return grants.candidates(db, matter_id, provider_contact_id)


@router.get("/matters/{matter_id}/shares", response_model=list[Grant])
def list_grants(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    return grants.list_grants(db, matter_id)


@router.get("/matters/{matter_id}/requests", response_model=list[ProviderRequest])
def provider_requests(matter_id: int, provider_contact_id: int, db: sqlite3.Connection = Depends(get_db)):
    return requests.requests_for(db, matter_id, provider_contact_id, audience="attorney")


@router.post("/shares", response_model=Grant)
def create_grant(body: CreateGrantRequest, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    return grants.create_grant(db, body, user)


@router.post("/shares/{grant_id}/release", response_model=ReleaseResult)
def release(grant_id: int, body: ReleaseRequest, db: sqlite3.Connection = Depends(get_db),
            user=Depends(current_user)):
    return grants.release(db, grant_id, body, user)


@router.post("/shares/{grant_id}/revoke", response_model=OkResponse)
def revoke(grant_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    grants.revoke(db, grant_id, user)
    return OkResponse()


@router.get("/shares/{grant_id}/audit", response_model=ShareAudit)
def audit(grant_id: int, db: sqlite3.Connection = Depends(get_db)):
    return grants.audit(db, grant_id)


@router.post("/requests/{request_id}/dismiss", response_model=OkResponse)
def dismiss_request(request_id: str, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    req = sources.provider_request(db, request_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    requests.set_state(db, request_id, "dismissed", user["id"])
    for g in db.execute("SELECT id FROM share_grants WHERE matter_id = ? AND provider_contact_id = ? "
                        "AND revoked_at IS NULL", (req["matter_id"], req["provider_contact_id"])).fetchall():
        latest = grants.latest_policy(db, g["id"])
        events.log_event(db, g["id"], "request_dismissed", user, version=latest.version if latest else None,
                         meta={"request_id": request_id})
    return OkResponse()
