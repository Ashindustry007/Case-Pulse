"""Documents: download (GET) → per-page text layer + page PNGs → pages without a text layer are marked `pending`
for OCR (ai/ocr.py). Re-processing is skipped when the document record's content hash is unchanged.

Files:  data/files/{doc_clio_id}.{ext}   data/pages/{doc_clio_id}/{n}.png   data/files/{doc_clio_id}.json (sidecar)
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

import pymupdf

from .. import config
from ..db import jload

log = logging.getLogger("casepulse.documents")
MIN_TEXT_CHARS = 40          # fewer characters than this on a page → treat as scanned, OCR it
RENDER_DPI = 130
IMAGE_TYPES = ("image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/tiff", "image/bmp")


def files_dir() -> Path:
    d = config.settings.data_dir / "files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def pages_dir(doc_key: str) -> Path:
    d = config.settings.data_dir / "pages" / doc_key
    d.mkdir(parents=True, exist_ok=True)
    return d


def doc_key(record_id: str) -> str:
    return record_id.split(":", 1)[1]


def file_path_for(record_id: str) -> Path | None:
    side = files_dir() / f"{doc_key(record_id)}.json"
    if not side.exists():
        return None
    p = files_dir() / json.loads(side.read_text())["file"]
    return p if p.exists() else None


def _ext(name: str, content_type: str | None) -> str:
    m = re.search(r"\.([A-Za-z0-9]{1,5})$", name or "")
    if m:
        return m.group(1).lower()
    ct = (content_type or "").lower()
    return {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg", "text/plain": "txt",
            "text/html": "html"}.get(ct, "bin")


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf8", "ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


def process_document(db: sqlite3.Connection, client: Any, rec: sqlite3.Row, *, force: bool = False) -> dict:
    """Ensure a document is downloaded and split into pages. Returns stats."""
    key = doc_key(rec["id"])
    side = files_dir() / f"{key}.json"
    meta = jload(rec["meta"], {}) or {}
    if not force and side.exists():
        info = json.loads(side.read_text())
        if info.get("record_hash") == rec["content_hash"] and db.execute(
                "SELECT 1 FROM document_pages WHERE document_id=? LIMIT 1", (rec["id"],)).fetchone():
            return {"skipped": 1}
    data, ctype = client.download(int(rec["clio_id"]))
    ctype = (ctype or meta.get("content_type") or "").split(";")[0].strip().lower()
    rel = meta.get("file_path")  # files/{id}.{ext} — the path Dev 2's adapter serves (relative to DATA_DIR)
    fname = rel.split("/", 1)[1] if rel and rel.startswith("files/") else f"{key}.{_ext(rec['title'], ctype)}"
    ext = fname.rsplit(".", 1)[-1]
    (files_dir() / fname).write_bytes(data)

    db.execute("DELETE FROM document_pages WHERE document_id=?", (rec["id"],))
    pages: list[tuple[int, str, str, str | None]] = []
    pdir = pages_dir(key)
    try:
        if ext == "pdf" or ctype == "application/pdf" or ext in ("xps", "epub"):
            doc = pymupdf.open(stream=data, filetype=ext if ext in ("xps", "epub") else "pdf")
            for i, page in enumerate(doc, start=1):
                text = page.get_text("text") or ""
                img = pdir / f"{i}.png"
                page.get_pixmap(dpi=RENDER_DPI).save(img)
                method = "text_layer" if len(text.strip()) >= MIN_TEXT_CHARS else "pending"
                pages.append((i, text if method == "text_layer" else "", method, str(img)))
        elif ctype in IMAGE_TYPES or ext in ("png", "jpg", "jpeg", "gif", "webp", "tif", "tiff", "bmp", "heic"):
            img = pdir / "1.png"
            try:
                pymupdf.Pixmap(data).save(img)
            except Exception:  # noqa: BLE001 — fall back through a document wrapper (handles tiff/jpeg variants)
                d = pymupdf.open(stream=data, filetype=ext)
                d[0].get_pixmap(dpi=RENDER_DPI).save(img)
            pages.append((1, "", "pending", str(img)))
        elif ext == "docx":
            pages.append((1, _docx_text(data), "text_layer", None))
        elif ext in ("txt", "csv", "md", "html", "htm", "eml") or ctype.startswith("text/"):
            from ..sync.render import strip_html

            t = data.decode("utf8", "ignore")
            pages.append((1, strip_html(t) if ext in ("html", "htm") else t, "text_layer", None))
        else:
            pages.append((1, "", "none", None))
    except Exception as e:  # noqa: BLE001 — a corrupt file must not stop the pipeline
        log.warning("document %s could not be parsed: %s", rec["id"], e)
        pages = [(1, "", "none", None)]

    for no, text, method, img in pages:
        db.execute("""INSERT INTO document_pages(document_id, page_no, text, method, image_path, text_hash)
                      VALUES (?,?,?,?,?,?)""",
                   (rec["id"], no, text, method, img, hashlib.sha256(text.encode()).hexdigest() if text else None))
    side.write_text(json.dumps({"file": fname, "content_type": ctype, "record_hash": rec["content_hash"],
                                "pages": len(pages)}))
    return {"processed": 1, "pages": len(pages), "pending_ocr": sum(1 for p in pages if p[2] == "pending")}


def process_matter_documents(db: sqlite3.Connection, client: Any, matter_id: int) -> dict:
    stats = {"documents": 0, "processed": 0, "skipped": 0, "pages": 0, "pending_ocr": 0, "errors": 0}
    rows = db.execute("SELECT * FROM records WHERE matter_id=? AND type='document' AND deleted_at IS NULL",
                      (matter_id,)).fetchall()
    for rec in rows:
        stats["documents"] += 1
        try:
            s = process_document(db, client, rec)
            db.commit()
        except Exception as e:  # noqa: BLE001
            log.warning("document %s failed: %s", rec["id"], e)
            stats["errors"] += 1
            continue
        for k in ("processed", "skipped", "pages", "pending_ocr"):
            stats[k] += s.get(k, 0)
    return stats
