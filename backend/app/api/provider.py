"""[Dev 2] Provider-role endpoints (F6, F7, F8). Output is ONLY ProviderProjection; every query is filtered by
grant ownership (404 otherwise); unshared sections are absent (exclude_none); views/doc opens are logged."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..auth import current_user, require_role
from ..contracts import OkResponse, ProviderCase, ProviderCaseSummary
from ..db import get_db
from ..sharing import access, events, grants, requests, sources

router = APIRouter(prefix="/api/provider", tags=["provider"], dependencies=[Depends(require_role("provider"))])


@router.get("/cases", response_model=list[ProviderCaseSummary])
def my_cases(db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    return access.summaries(db, user)


@router.get("/cases/{grant_id}", response_model=ProviderCase, response_model_exclude_none=True)
def my_case(grant_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    grant, policy = access.owned_grant(db, grant_id, user)
    case = access.case_for(db, grant, policy)
    events.log_event(db, grant_id, "viewed", user, version=policy.version)
    return case


@router.get("/cases/{grant_id}/documents/{document_id}")
def my_document(grant_id: int, document_id: str, db: sqlite3.Connection = Depends(get_db),
                user=Depends(current_user)):
    grant, policy = access.owned_grant(db, grant_id, user)
    if "documents" not in policy.fields or document_id not in policy.document_ids:
        raise HTTPException(404, "Document not found")
    path = sources.document_path(db, grant["matter_id"], document_id)
    if path is None:
        raise HTTPException(404, "Document file not available")
    events.log_event(db, grant_id, "document_opened", user, version=policy.version,
                     meta={"document_id": document_id})
    return FileResponse(path)  # no filename → no attachment header → browser renders inline


@router.post("/requests/{request_id}/complete", response_model=OkResponse)
def complete_request(request_id: str, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    req = sources.provider_request(db, request_id)
    grant = req and db.execute(
        "SELECT id FROM share_grants WHERE matter_id = ? AND provider_contact_id = ? AND provider_user_id = ? "
        "AND revoked_at IS NULL ORDER BY id DESC LIMIT 1",
        (req["matter_id"], req["provider_contact_id"], user["id"])).fetchone()
    policy = grant and grants.latest_policy(db, grant["id"])
    if not policy or "open_requests" not in policy.fields:
        raise HTTPException(404, "Request not found")
    requests.set_state(db, request_id, "completed", user["id"])
    events.log_event(db, grant["id"], "request_completed", user, version=policy.version,
                     meta={"request_id": request_id})
    return OkResponse()
