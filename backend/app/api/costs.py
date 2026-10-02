"""[Dev 1] AI cost monitoring (F10). PHASE 0 STUB."""
from fastapi import APIRouter, Depends

from ..auth import require_role
from ..contracts import AiCostReport, FirmCostReport
from ..stubs import fixture

router = APIRouter(prefix="/api/ai-costs", tags=["costs"], dependencies=[Depends(require_role("attorney"))])


@router.get("", response_model=AiCostReport)
def matter_costs(matter_id: int | None = None, date_from: str | None = None, date_to: str | None = None):
    return fixture("ai_costs", AiCostReport)


@router.get("/firm", response_model=FirmCostReport)
def firm_costs(days: int = 30):
    return fixture("firm_costs", FirmCostReport)
