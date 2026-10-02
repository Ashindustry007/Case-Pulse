"""[Dev 1] Digestion pipeline trigger + run history (F9). PHASE 0 STUB."""
from fastapi import APIRouter, Depends

from ..auth import require_role
from ..contracts import DigestRun
from ..stubs import fixture

router = APIRouter(prefix="/api", tags=["digest"], dependencies=[Depends(require_role("attorney"))])


@router.post("/digest/{matter_id}", response_model=DigestRun)
def run_digest(matter_id: int):
    return fixture("digest_run", DigestRun)


@router.get("/matters/{matter_id}/digest-runs", response_model=list[DigestRun])
def digest_runs(matter_id: int):
    return fixture("digest_runs", list[DigestRun])
