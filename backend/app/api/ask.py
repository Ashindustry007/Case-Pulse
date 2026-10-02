"""[Dev 1] Ask the case (RAG, SSE), locate/verify a highlighted passage, provider status-note draft.

SSE protocol for POST /api/matters/{id}/ask  (Content-Type: text/event-stream):
  event: status    data: {"message": "..."}      progress ("Searching: ...")
  event: segment   data: AnswerSegment JSON      one per answer text block, in order; citations [] if uncited
  event: done      data: {"followups": [...], "cost_usd": 0.08}
  event: error     data: {"message": "..."}
"""
from __future__ import annotations

import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..ai.assist import locate as do_locate
from ..ai.assist import provider_draft as do_draft
from ..auth import require_role
from ..contracts import AskRequest, LocateRequest, LocateResult, ProviderDraft, ProviderDraftRequest
from ..db import get_db
from ..llm import LLMNotConfigured
from ..rag.answer import ask_stream
from .matters import get_matter

router = APIRouter(prefix="/api/matters", tags=["ask"])
attorney = require_role("attorney")


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/{matter_id}/ask", response_class=StreamingResponse,
             responses={200: {"content": {"text/event-stream": {}}, "description": "SSE stream, see module doc"}})
def ask(matter_id: int, body: AskRequest, user=Depends(attorney), db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    history = [t.model_dump() for t in body.history]

    def gen():
        try:
            for event, data in ask_stream(matter_id, user["id"], body.question, history):
                yield sse(event, data)
        except LLMNotConfigured as e:
            yield sse("error", {"message": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/{matter_id}/locate", response_model=LocateResult, dependencies=[Depends(attorney)])
def locate(matter_id: int, body: LocateRequest, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    try:
        return do_locate(db, matter_id, body.text)
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))


@router.post("/{matter_id}/provider-draft", response_model=ProviderDraft, dependencies=[Depends(attorney)])
def provider_draft(matter_id: int, body: ProviderDraftRequest, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    try:
        return do_draft(db, matter_id, body.provider_contact_id, list(body.fields))
    except LLMNotConfigured as e:
        raise HTTPException(503, str(e))
