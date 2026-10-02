"""Build/refresh the retrieval index for a matter: chunks (+ sentence units) → FTS5 + sqlite-vec (local embeddings).

Hash-gated per source (record body or document page): unchanged sources are skipped, changed ones re-chunked.
Embeddings: fastembed BAAI/bge-base-en-v1.5 (768-d), run locally — no case text leaves the machine for embedding.
"""
from __future__ import annotations

import hashlib
import logging
import sqlite3
import threading
import time

import numpy as np

from .. import config
from ..db import jdump, now_iso
from ..llm import log_local_run
from .chunker import chunk_text

log = logging.getLogger("casepulse.rag")
CHUNKER_VERSION = "v1"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
_model = None
_model_lock = threading.Lock()


def embedder():
    global _model
    with _model_lock:
        if _model is None:
            from fastembed import TextEmbedding

            _model = TextEmbedding(model_name=config.settings.embed_model)
    return _model


def embed_passages(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 768), dtype=np.float32)
    return np.array(list(embedder().embed(texts, batch_size=32)), dtype=np.float32)


def embed_query(q: str) -> np.ndarray:
    return np.array(list(embedder().embed([QUERY_PREFIX + q])), dtype=np.float32)[0]


def _sources(db: sqlite3.Connection, matter_id: int) -> list[dict]:
    """Every citable text source of the matter: record bodies + document pages."""
    out = []
    for r in db.execute("""SELECT id, type, title, occurred_at, body_text, content_hash FROM records
                           WHERE matter_id=? AND deleted_at IS NULL""", (matter_id,)):
        if r["body_text"].strip():
            out.append({"record_id": r["id"], "page": None, "text": r["body_text"], "title": r["title"],
                        "type": r["type"], "date": r["occurred_at"], "hash": r["content_hash"]})
    for p in db.execute("""SELECT p.document_id, p.page_no, p.text, p.text_hash, r.title, r.occurred_at
                           FROM document_pages p JOIN records r ON r.id=p.document_id
                           WHERE r.matter_id=? AND r.deleted_at IS NULL AND p.text != ''""", (matter_id,)):
        out.append({"record_id": p["document_id"], "page": p["page_no"], "text": p["text"], "title": p["title"],
                    "type": "document", "date": p["occurred_at"],
                    "hash": p["text_hash"] or hashlib.sha256(p["text"].encode()).hexdigest()})
    return out


def _delete_chunks(db: sqlite3.Connection, ids: list[int]) -> None:
    for cid in ids:
        db.execute("DELETE FROM chunk_vectors WHERE rowid=?", (cid,))
        db.execute("DELETE FROM chunks_fts WHERE rowid=?", (cid,))
    if ids:
        db.execute(f"DELETE FROM chunks WHERE id IN ({','.join('?' * len(ids))})", ids)


def build_index(db: sqlite3.Connection, matter_id: int) -> dict:
    t0 = time.monotonic()
    sources = _sources(db, matter_id)
    stats = {"sources": len(sources), "skipped": 0, "reindexed": 0, "chunks": 0, "removed": 0}
    live_keys = set()
    pending: list[tuple[dict, list]] = []
    for s in sources:
        key = (s["record_id"], s["page"])
        live_keys.add(key)
        h = hashlib.sha256(f"{CHUNKER_VERSION}|{s['hash']}|{s['title']}".encode()).hexdigest()
        existing = db.execute("SELECT id, content_hash FROM chunks WHERE record_id=? AND page_no IS ?",
                              (s["record_id"], s["page"])).fetchall()
        if existing and all(e["content_hash"] == h for e in existing):
            stats["skipped"] += 1
            continue
        _delete_chunks(db, [e["id"] for e in existing])
        s["chunk_hash"] = h
        pending.append((s, chunk_text(s["text"])))
        stats["reindexed"] += 1

    # remove chunks whose source disappeared (deleted record / re-paged document)
    stale = [r["id"] for r in db.execute("SELECT id, record_id, page_no FROM chunks WHERE matter_id=?", (matter_id,))
             if (r["record_id"], r["page_no"]) not in live_keys]
    _delete_chunks(db, stale)
    stats["removed"] = len(stale)

    rows, embed_inputs = [], []
    for s, chunks in pending:
        for ch in chunks:
            rows.append((s, ch))
            header = f"{s['type'].replace('_', ' ')}: {s['title']}" + (f" (page {s['page']})" if s["page"] else "")
            embed_inputs.append(f"{header}\n{ch.text}")
    vecs = embed_passages(embed_inputs)
    now = now_iso()
    for (s, ch), vec, text_for_fts in zip(rows, vecs, embed_inputs):
        cur = db.execute(
            """INSERT INTO chunks(matter_id, record_id, page_no, char_start, char_end, text, units, content_hash,
                 created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
            (matter_id, s["record_id"], s["page"], ch.char_start, ch.char_end, ch.text, jdump(ch.units),
             s["chunk_hash"], now))
        cid = cur.lastrowid
        db.execute("INSERT INTO chunk_vectors(rowid, matter_id, embedding) VALUES (?,?,?)",
                   (cid, matter_id, vec.astype(np.float32).tobytes()))
        db.execute("INSERT INTO chunks_fts(rowid, text) VALUES (?,?)", (cid, text_for_fts))
    stats["chunks"] = len(rows)
    db.commit()
    if rows:
        log_local_run("embed", config.settings.embed_model, matter_id=matter_id,
                      duration_ms=int((time.monotonic() - t0) * 1000))
    return stats
