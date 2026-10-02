"""Hybrid retrieval: sqlite-vec KNN + FTS5 bm25, fused with reciprocal rank fusion, then metadata filters."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field

import numpy as np

from ..db import jload
from .index import embed_query

RRF_K = 60
_STOP = set("""a an and are as at be by for from has have how i in is it its of on or that the this to was were what
when where which who why will with did does do any about there their they them we our you your me my""".split())


@dataclass
class Hit:
    chunk_id: int
    record_id: str
    page: int | None
    char_start: int
    char_end: int
    text: str
    units: list[tuple[int, int]]
    type: str
    title: str
    date: str | None
    author: str | None
    clio_url: str | None
    score: float = 0.0
    meta: dict = field(default_factory=dict)

    def unit_texts(self) -> list[str]:
        return [self.text[s - self.char_start:e - self.char_start] for s, e in self.units]


def fts_query(q: str) -> str | None:
    toks = [t for t in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]*", q.lower()) if t not in _STOP and len(t) > 1]
    if not toks:
        return None
    return " OR ".join(f'"{t}"' for t in dict.fromkeys(toks))


def _vector_ids(db: sqlite3.Connection, matter_id: int, query: str, k: int) -> list[int]:
    vec = embed_query(query).astype(np.float32).tobytes()
    rows = db.execute("SELECT rowid FROM chunk_vectors WHERE embedding MATCH ? AND k = ? AND matter_id = ? "
                      "ORDER BY distance", (vec, k, matter_id)).fetchall()
    return [r[0] for r in rows]


def _fts_ids(db: sqlite3.Connection, matter_id: int, query: str, k: int) -> list[int]:
    q = fts_query(query)
    if not q:
        return []
    rows = db.execute("""SELECT f.rowid FROM chunks_fts f JOIN chunks c ON c.id = f.rowid
                         WHERE chunks_fts MATCH ? AND c.matter_id = ? ORDER BY bm25(chunks_fts) LIMIT ?""",
                      (q, matter_id, k)).fetchall()
    return [r[0] for r in rows]


def hydrate(db: sqlite3.Connection, ids: list[int]) -> dict[int, Hit]:
    if not ids:
        return {}
    rows = db.execute(f"""SELECT c.*, r.type, r.title, r.occurred_at, r.author, r.clio_url, r.meta FROM chunks c
                          JOIN records r ON r.id = c.record_id WHERE c.id IN ({','.join('?' * len(ids))})""", ids)
    out = {}
    for r in rows:
        out[r["id"]] = Hit(chunk_id=r["id"], record_id=r["record_id"], page=r["page_no"], char_start=r["char_start"],
                           char_end=r["char_end"], text=r["text"], units=[tuple(u) for u in jload(r["units"], [])],
                           type=r["type"], title=r["title"] or r["type"], date=r["occurred_at"], author=r["author"],
                           clio_url=r["clio_url"], meta=jload(r["meta"], {}) or {})
    return out


def hybrid_search(db: sqlite3.Connection, matter_id: int, query: str, *, types: list[str] | None = None,
                  date_from: str | None = None, date_to: str | None = None, k: int = 12,
                  exclude_types: tuple[str, ...] = ()) -> list[Hit]:
    pool = 30 if not (types or date_from or date_to) else 80
    vec_ids = _vector_ids(db, matter_id, query, pool)
    fts_ids = _fts_ids(db, matter_id, query, pool)
    scores: dict[int, float] = {}
    for ranked in (vec_ids, fts_ids):
        for rank, cid in enumerate(ranked):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
    hits = hydrate(db, list(scores))
    out = []
    for cid, score in sorted(scores.items(), key=lambda kv: -kv[1]):
        h = hits.get(cid)
        if h is None:
            continue
        if types and h.type not in types:
            continue
        if h.type in exclude_types:
            continue
        d = (h.date or "")[:10]
        if date_from and d and d < date_from[:10]:
            continue
        if date_to and d and d > date_to[:10]:
            continue
        h.score = score
        out.append(h)
        if len(out) >= k:
            break
    return out
