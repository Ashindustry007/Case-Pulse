"""[Dev 1] Ask (RAG, SSE), locate, provider draft. PHASE 0 STUB.

SSE protocol for POST /api/matters/{id}/ask  (Content-Type: text/event-stream):
  event: segment   data: AnswerSegment JSON      (one per answer text block, in order; citations [] if uncited)
  event: status    data: {"message": "..."}      (optional progress, e.g. "Searching the case file…")
  event: done      data: {"followups": [...], "cost_usd": 0.08}
  event: error     data: {"message": "..."}
"""
import json
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..auth import require_role
from ..contracts import (Answer, AskRequest, LocateRequest, LocateResult, ProviderDraft, ProviderDraftRequest)
from ..stubs import fixture

router = APIRouter(prefix="/api/matters", tags=["ask"], dependencies=[Depends(require_role("attorney"))])


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/{matter_id}/ask", response_class=StreamingResponse,
             responses={200: {"content": {"text/event-stream": {}}, "description": "SSE stream, see module doc"}})
def ask(matter_id: int, body: AskRequest):
    answer = fixture("answer", Answer)

    def gen():
        yield sse("status", {"message": "Searching the case file…"})
        for seg in answer.segments:
            time.sleep(0.2)
            yield sse("segment", seg.model_dump(mode="json"))
        yield sse("done", {"followups": answer.followups, "cost_usd": answer.cost_usd})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/{matter_id}/locate", response_model=LocateResult)
def locate(matter_id: int, body: LocateRequest):
    return fixture("locate", LocateResult)


@router.post("/{matter_id}/provider-draft", response_model=ProviderDraft)
def provider_draft(matter_id: int, body: ProviderDraftRequest):
    return fixture("provider_draft", ProviderDraft)
