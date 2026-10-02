"""[Dev 1] Brief (F2/F4/story), F1 visits/changes/delta, suggested questions. PHASE 0 STUB."""
from fastapi import APIRouter, Depends

from ..auth import require_role
from ..contracts import Brief, Changes, Delta, SuggestedQuestions, VisitResponse
from ..stubs import fixture

router = APIRouter(prefix="/api/matters", tags=["brief"], dependencies=[Depends(require_role("attorney"))])


@router.get("/{matter_id}/brief", response_model=Brief)
def brief(matter_id: int):
    return fixture("brief", Brief)


@router.post("/{matter_id}/visits", response_model=VisitResponse)
def visit(matter_id: int):
    return fixture("visit", VisitResponse)


@router.get("/{matter_id}/changes", response_model=Changes)
def changes(matter_id: int, since: str | None = None):
    return fixture("changes", Changes)


@router.get("/{matter_id}/delta", response_model=Delta)
def delta(matter_id: int, since: str | None = None):
    return fixture("delta", Delta)


@router.get("/{matter_id}/suggested-questions", response_model=SuggestedQuestions)
def suggested_questions(matter_id: int):
    return fixture("suggested_questions", SuggestedQuestions)
