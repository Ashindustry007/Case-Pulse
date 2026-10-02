"""OCR for scanned pages (document_pages.method = 'pending') with Claude Haiku vision.
Faithful transcription only — the text becomes the citation source, so it must not be summarized or "fixed".
Each page is OCR'd once; results persist in document_pages (that is the cache).
"""
from __future__ import annotations

import base64
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from ..config import settings
from ..llm import call_claude, text_of

log = logging.getLogger("casepulse.ocr")
OCR_PROMPT = (
    "Transcribe ALL text on this page exactly as written, top to bottom, preserving line breaks. "
    "Include headers, tables (one row per line, cells separated by ' | '), handwriting you can read, dates and numbers "
    "exactly. Do not summarize, correct, translate or add commentary. Mark unreadable words as [illegible]. "
    "If the page has no text at all, output exactly: [no text]")


def _ocr_one(matter_id: int, image_path: str) -> str:
    data = base64.standard_b64encode(Path(image_path).read_bytes()).decode()
    msg = call_claude("ocr", settings.model_fast, matter_id=matter_id, max_tokens=4096, messages=[{
        "role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}},
            {"type": "text", "text": OCR_PROMPT}]}])
    text = text_of(msg).strip()
    return "" if text == "[no text]" else text


def ocr_pending_pages(db: sqlite3.Connection, matter_id: int, workers: int = 8) -> dict:
    rows = db.execute(
        """SELECT p.document_id, p.page_no, p.image_path FROM document_pages p JOIN records r ON r.id = p.document_id
           WHERE r.matter_id=? AND p.method='pending' AND p.image_path IS NOT NULL""", (matter_id,)).fetchall()
    stats = {"pages": len(rows), "ocr_done": 0, "errors": 0}
    if not rows:
        return stats
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(_ocr_one, matter_id, r["image_path"]): r for r in rows}
        for fut in as_completed(futs):
            r = futs[fut]
            try:
                text = fut.result()
            except Exception as e:  # noqa: BLE001
                log.warning("OCR failed for %s p%s: %s", r["document_id"], r["page_no"], e)
                stats["errors"] += 1
                continue
            db.execute("UPDATE document_pages SET text=?, method='ocr' WHERE document_id=? AND page_no=?",
                       (text, r["document_id"], r["page_no"]))
            db.commit()
            stats["ocr_done"] += 1
    return stats
