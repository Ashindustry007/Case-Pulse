"""[Dev 1] Source records + document pages/files — the Source Drawer behind every citation (F3)."""
from __future__ import annotations

import mimetypes
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..auth import require_role
from ..contracts import DocumentPage, SourceRecord
from ..db import get_db, jload
from ..documents.processor import file_path_for

router = APIRouter(prefix="/api", tags=["records"], dependencies=[Depends(require_role("attorney"))])


def _record(db: sqlite3.Connection, record_id: str) -> sqlite3.Row:
    r = db.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
    if r is None:
        raise HTTPException(404, "Record not found")
    return r


@router.get("/records/{record_id}", response_model=SourceRecord)
def get_record(record_id: str, db: sqlite3.Connection = Depends(get_db)):
    r = _record(db, record_id)
    pages = db.execute("SELECT COUNT(*) FROM document_pages WHERE document_id=?", (record_id,)).fetchone()[0]
    return SourceRecord(record_id=r["id"], type=r["type"], title=r["title"] or r["type"], author=r["author"],
                        occurred_at=r["occurred_at"], body_text=r["body_text"],
                        participants=jload(r["participants"], []) or [], page_count=pages or None,
                        clio_url=r["clio_url"], meta=jload(r["meta"], {}) or {})


@router.get("/documents/{document_id}/pages/{page_no}", response_model=DocumentPage)
def get_page(document_id: str, page_no: int, db: sqlite3.Connection = Depends(get_db)):
    p = db.execute("SELECT * FROM document_pages WHERE document_id=? AND page_no=?", (document_id, page_no)).fetchone()
    if p is None:
        raise HTTPException(404, "Page not found")
    n = db.execute("SELECT COUNT(*) FROM document_pages WHERE document_id=?", (document_id,)).fetchone()[0]
    return DocumentPage(document_id=document_id, page_no=page_no, page_count=n, text=p["text"], method=p["method"],
                        image_url=f"/api/documents/{document_id}/pages/{page_no}/image" if p["image_path"] else None)


@router.get("/documents/{document_id}/pages/{page_no}/image")
def get_page_image(document_id: str, page_no: int, db: sqlite3.Connection = Depends(get_db)):
    p = db.execute("SELECT image_path FROM document_pages WHERE document_id=? AND page_no=?",
                   (document_id, page_no)).fetchone()
    if p is None or not p["image_path"] or not Path(p["image_path"]).exists():
        raise HTTPException(404, "No page image")
    return FileResponse(p["image_path"], media_type="image/png")


@router.get("/documents/{document_id}/file")
def get_file(document_id: str, db: sqlite3.Connection = Depends(get_db)):
    r = _record(db, document_id)
    path = file_path_for(document_id)
    if path is None:
        raise HTTPException(404, "Document not downloaded yet — run the digestion pipeline")
    media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media, filename=r["title"] or path.name,
                        content_disposition_type="inline")
