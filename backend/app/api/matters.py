"""[Dev 1] Attorney matter data endpoints (overview, timeline, deadlines, costs, providers). All facts cited (F3)."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..ai import views
from ..auth import require_role
from ..clio.client import connection_status
from ..contracts import Costs, Deadlines, MatterSummary, Overview, Providers, Timeline
from ..db import get_db, jdump, now_iso

router = APIRouter(prefix="/api/matters", tags=["matters"], dependencies=[Depends(require_role("attorney"))])


def get_matter(db: sqlite3.Connection, matter_id: int) -> sqlite3.Row:
    m = db.execute("SELECT * FROM matters WHERE id=?", (matter_id,)).fetchone()
    if m is None:
        raise HTTPException(404, "Matter not synced yet — POST /api/sync/{matter_id}")
    return m


@router.get("", response_model=list[MatterSummary])
def list_matters(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM matters ORDER BY display_number").fetchall()
    if not rows and connection_status()["connected"]:
        # First visit after connecting Clio: discover matters (1 GET), records are pulled on open/sync.
        from ..sync.engine import list_clio_matters

        for m in list_clio_matters():
            db.execute("""INSERT OR IGNORE INTO matters(id, display_number, description, status, client_id, raw, synced_at)
                          VALUES (?,?,?,?,?,?,?)""", (m["id"], m.get("display_number"), m.get("description"),
                                                      m.get("status"), (m.get("client") or {}).get("id"), jdump(m),
                                                      now_iso()))
            if (m.get("client") or {}).get("id"):
                db.execute("INSERT OR IGNORE INTO contacts(id, name, synced_at) VALUES (?,?,?)",
                           (m["client"]["id"], m["client"].get("name"), now_iso()))
        rows = db.execute("SELECT * FROM matters ORDER BY display_number").fetchall()
    return [views.matter_summary(db, m) for m in rows]


@router.get("/{matter_id}/overview", response_model=Overview)
def overview(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    return views.overview(db, get_matter(db, matter_id))


@router.get("/{matter_id}/timeline", response_model=Timeline)
def timeline(matter_id: int, types: str | None = None, since: str | None = None, q: str | None = None,
             limit: int = 500, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    items, total = views.timeline(db, matter_id, [t for t in (types or "").split(",") if t] or None, since, q, limit)
    return Timeline(items=items, total=total)


@router.get("/{matter_id}/deadlines", response_model=Deadlines)
def deadlines(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    return views.deadlines(db, matter_id)


@router.get("/{matter_id}/costs", response_model=Costs)
def costs(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    return views.costs(db, matter_id)


@router.get("/{matter_id}/providers", response_model=Providers)
def providers(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    return Providers(providers=views.provider_summaries(db, matter_id))


@router.get("/{matter_id}/client-photo", summary="Cropped client photo (from Clio avatar or a photo/ID document)")
def client_photo(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    from pathlib import Path

    from ..db import jload

    row = db.execute("SELECT value FROM facts WHERE matter_id=? AND kind='client_photo' ORDER BY id DESC LIMIT 1",
                     (matter_id,)).fetchone()
    path = (jload(row["value"], {}) or {}).get("image_path") if row else None
    if not path or not Path(path).exists():
        raise HTTPException(404, "No client photo found in the file")
    return FileResponse(path, media_type="image/png")
