"""[Dev 1] Digestion pipeline trigger + run history (F9)."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..ai.pipeline import run_pipeline, run_to_contract
from ..auth import require_role
from ..clio.client import ClioClient, connection_status
from ..contracts import DigestRun
from ..db import get_db
from .matters import get_matter

router = APIRouter(prefix="/api", tags=["digest"], dependencies=[Depends(require_role("attorney"))])


@router.post("/digest/{matter_id}", response_model=DigestRun)
def run_digest(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    db.commit()
    clio = ClioClient() if connection_status()["connected"] else None
    return run_to_contract(run_pipeline(matter_id, trigger="api", clio=clio))


@router.get("/matters/{matter_id}/digest-runs", response_model=list[DigestRun])
def digest_runs(matter_id: int, limit: int = 20, db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM digest_runs WHERE matter_id=? ORDER BY id DESC LIMIT ?", (matter_id, limit))
    return [run_to_contract(r) for r in rows]
