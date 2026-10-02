"""[Dev 1] Attorney matter data endpoints. PHASE 0 STUB — replaced on feat/intelligence."""
from fastapi import APIRouter, Depends

from ..auth import require_role
from ..contracts import Costs, Deadlines, MatterSummary, Overview, Providers, Timeline
from ..stubs import fixture

router = APIRouter(prefix="/api/matters", tags=["matters"], dependencies=[Depends(require_role("attorney"))])


@router.get("", response_model=list[MatterSummary])
def list_matters():
    return fixture("matters", list[MatterSummary])


@router.get("/{matter_id}/overview", response_model=Overview)
def overview(matter_id: int):
    return fixture("overview", Overview)


@router.get("/{matter_id}/timeline", response_model=Timeline)
def timeline(matter_id: int, types: str | None = None, since: str | None = None, q: str | None = None,
             limit: int = 500):
    return fixture("timeline", Timeline)


@router.get("/{matter_id}/deadlines", response_model=Deadlines)
def deadlines(matter_id: int):
    return fixture("deadlines", Deadlines)


@router.get("/{matter_id}/costs", response_model=Costs)
def costs(matter_id: int):
    return fixture("costs", Costs)


@router.get("/{matter_id}/providers", response_model=Providers)
def providers(matter_id: int):
    return fixture("providers", Providers)
