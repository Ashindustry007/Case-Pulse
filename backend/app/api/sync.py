"""[Dev 1] Clio connection + sync. PHASE 0 STUB — replaced on feat/intelligence."""
from fastapi import APIRouter, Depends

from ..auth import public, require_role
from ..contracts import OkResponse, SyncResult, SyncStatus
from ..stubs import fixture

router = APIRouter(tags=["sync"])
attorney = [Depends(require_role("attorney"))]


@router.get("/auth/clio/login", dependencies=attorney, response_model=OkResponse)
def clio_login():
    return OkResponse(ok=False, message="stub: redirects to Clio OAuth once implemented")


@router.get("/auth/clio/callback", dependencies=[Depends(public)], response_model=OkResponse)
def clio_callback(code: str | None = None, state: str | None = None):
    return OkResponse(ok=False, message="stub")


@router.post("/api/sync/{matter_id}", dependencies=attorney, response_model=SyncResult)
def sync_matter(matter_id: int):
    return fixture("sync_result", SyncResult)


@router.get("/api/sync/status", dependencies=attorney, response_model=SyncStatus)
def sync_status():
    return fixture("sync_status", SyncStatus)
