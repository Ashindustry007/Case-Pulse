"""[Dev 2] Provider-role endpoints (F6, F7, F8). PHASE 0 STUB.
Real version: ONLY ProviderProjection output; ownership filter on every query; unshared sections absent
(response_model_exclude_none=True); views/doc opens logged to share_events."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import require_role
from ..contracts import OkResponse, ProviderCase, ProviderCaseSummary
from ..stubs import fixture

router = APIRouter(prefix="/api/provider", tags=["provider"], dependencies=[Depends(require_role("provider"))])


@router.get("/cases", response_model=list[ProviderCaseSummary])
def my_cases():
    return fixture("provider_cases", list[ProviderCaseSummary])


@router.get("/cases/{grant_id}", response_model=ProviderCase, response_model_exclude_none=True)
def my_case(grant_id: int):
    return fixture("provider_case", ProviderCase)


@router.get("/cases/{grant_id}/documents/{document_id}")
def my_document(grant_id: int, document_id: str):
    raise HTTPException(404, "stub")


@router.post("/requests/{request_id}/complete", response_model=OkResponse)
def complete_request(request_id: str):
    return OkResponse(message="stub")
