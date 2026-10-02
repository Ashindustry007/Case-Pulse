"""[Dev 2] Share grants, versioned policies, candidates, audit (F5, F7, F8). PHASE 0 STUB."""
from fastapi import APIRouter, Depends

from ..auth import require_role
from ..contracts import (CreateGrantRequest, Grant, OkResponse, ReleaseRequest, ReleaseResult, ShareAudit,
                         ShareCandidates)
from ..stubs import fixture

router = APIRouter(prefix="/api", tags=["shares"], dependencies=[Depends(require_role("attorney"))])


@router.get("/matters/{matter_id}/share-candidates", response_model=ShareCandidates)
def share_candidates(matter_id: int, provider_contact_id: int):
    return fixture("share_candidates", ShareCandidates)


@router.get("/matters/{matter_id}/shares", response_model=list[Grant])
def list_grants(matter_id: int):
    return fixture("grants", list[Grant])


@router.post("/shares", response_model=Grant)
def create_grant(body: CreateGrantRequest):
    return fixture("grant", Grant)


@router.post("/shares/{grant_id}/release", response_model=ReleaseResult)
def release(grant_id: int, body: ReleaseRequest):
    return fixture("release_result", ReleaseResult)


@router.post("/shares/{grant_id}/revoke", response_model=OkResponse)
def revoke(grant_id: int):
    return OkResponse(message="stub")


@router.get("/shares/{grant_id}/audit", response_model=ShareAudit)
def audit(grant_id: int):
    return fixture("share_audit", ShareAudit)


@router.post("/requests/{request_id}/dismiss", response_model=OkResponse)
def dismiss_request(request_id: str):
    return OkResponse(message="stub")
