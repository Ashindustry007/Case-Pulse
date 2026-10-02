"""Citations (F3): every path that produces a `Citation` lives here.

1. RAG: hits → Claude `search_result` blocks (one text block per sentence unit) and back from `search_result_location`.
2. AI facts: verify a model-supplied quote inside a chunk/record (fuzzy) → exact offsets, or None (fact dropped).
3. Structured Clio facts: deterministic citation to a record line (e.g. "Medical bill · X · $22,140.00 · 2025-05-02").
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from rapidfuzz import fuzz

from ..contracts import Citation
from ..db import jload
from .search import Hit

MIN_QUOTE_SCORE = 88


def _citation(*, record_id: str, rtype: str, title: str, author: str | None, date: str | None, page: int | None,
              start: int, end: int, excerpt: str, clio_url: str | None) -> Citation:
    return Citation(record_id=record_id, source_type=rtype, title=title or rtype, author=author, date=date,
                    page=page, char_start=max(0, start), char_end=max(start, end), excerpt=excerpt.strip() or title,
                    clio_url=clio_url)


# ---------------------------------------------------------------------------------------------------------------
# 1. search_result blocks ⇄ citations
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class ResultRegistry:
    """Tracks every search_result block sent in a conversation, in order (search_result_index is global)."""
    hits: list[Hit] = field(default_factory=list)

    def blocks(self, hits: list[Hit]) -> list[dict]:
        out = []
        for h in hits:
            self.hits.append(h)
            label = h.type.replace("_", " ")
            when = f" · {h.date[:10]}" if h.date else ""
            page = f" · page {h.page}" if h.page else ""
            out.append({
                "type": "search_result",
                "source": f"{h.record_id}#p{h.page}" if h.page else h.record_id,
                "title": f"{label}: {h.title}{page}{when}",
                "content": [{"type": "text", "text": t} for t in h.unit_texts()] or [{"type": "text", "text": h.text}],
                "citations": {"enabled": True},
            })
        return out

    def to_citation(self, loc: Any) -> Citation | None:
        idx = getattr(loc, "search_result_index", None)
        if idx is None or idx >= len(self.hits):
            return None
        h = self.hits[idx]
        s_blk = getattr(loc, "start_block_index", 0) or 0
        e_blk = getattr(loc, "end_block_index", s_blk + 1) or (s_blk + 1)
        units = h.units or [(h.char_start, h.char_end)]
        s_blk = min(s_blk, len(units) - 1)
        e_blk = max(s_blk + 1, min(e_blk, len(units)))
        start, end = units[s_blk][0], units[e_blk - 1][1]
        # Excerpt = the exact source slice (Claude's cited_text drops line-break whitespace between blocks).
        excerpt = h.text[start - h.char_start:end - h.char_start] or getattr(loc, "cited_text", "")
        return _citation(record_id=h.record_id, rtype=h.type, title=h.title, author=h.author, date=h.date,
                         page=h.page, start=start, end=end, excerpt=excerpt, clio_url=h.clio_url)


# ---------------------------------------------------------------------------------------------------------------
# 2. verify model quotes → exact offsets
# ---------------------------------------------------------------------------------------------------------------
def _source_text(db: sqlite3.Connection, record_id: str, page: int | None) -> tuple[str, sqlite3.Row] | None:
    rec = db.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
    if rec is None:
        return None
    if page:
        p = db.execute("SELECT text FROM document_pages WHERE document_id=? AND page_no=?", (record_id, page)).fetchone()
        return (p["text"], rec) if p else None
    return rec["body_text"], rec


def _align(quote: str, text: str) -> tuple[int, int, float] | None:
    q = " ".join(quote.split())
    if not q or not text:
        return None
    i = text.find(quote.strip())
    if i >= 0:
        return i, i + len(quote.strip()), 100.0
    res = fuzz.partial_ratio_alignment(q, text, score_cutoff=MIN_QUOTE_SCORE)
    if res is None:
        return None
    s, e = res.dest_start, res.dest_end
    while s > 0 and not text[s - 1].isspace():  # widen to whole words
        s -= 1
    while e < len(text) and not text[e].isspace() and text[e] not in ".,;":
        e += 1
    return s, e, res.score


def verify_quote(db: sqlite3.Connection, record_id: str, page: int | None, quote: str) -> Citation | None:
    src = _source_text(db, record_id, page)
    if not src:
        return None
    text, rec = src
    al = _align(quote, text)
    if not al:
        return None
    s, e, _ = al
    return _citation(record_id=rec["id"], rtype=rec["type"], title=rec["title"], author=rec["author"],
                     date=rec["occurred_at"], page=page, start=s, end=e, excerpt=text[s:e], clio_url=rec["clio_url"])


def verify_chunk_quote(db: sqlite3.Connection, chunk_id: int, quote: str) -> Citation | None:
    ch = db.execute("SELECT record_id, page_no FROM chunks WHERE id=?", (chunk_id,)).fetchone()
    if ch is None:
        return None
    return verify_quote(db, ch["record_id"], ch["page_no"], quote)


# ---------------------------------------------------------------------------------------------------------------
# 3. deterministic citations for structured records
# ---------------------------------------------------------------------------------------------------------------
def record_citation(db: sqlite3.Connection, record_id: str, contains: str | None = None,
                    rec: sqlite3.Row | None = None) -> Citation | None:
    """Cite a whole line of a record: the line containing `contains`, else the first line."""
    rec = rec or db.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
    if rec is None:
        return None
    text = rec["body_text"] or rec["title"] or ""
    start = 0
    if contains:
        i = text.lower().find(contains.lower())
        if i >= 0:
            start = text.rfind("\n", 0, i) + 1
    end = text.find("\n", start)
    end = len(text) if end < 0 else end
    if end <= start:
        end = len(text)
    return _citation(record_id=rec["id"], rtype=rec["type"], title=rec["title"], author=rec["author"],
                     date=rec["occurred_at"], page=None, start=start, end=end, excerpt=text[start:end] or rec["title"],
                     clio_url=rec["clio_url"])


def citations_from_json(raw: str | None) -> list[Citation]:
    return [Citation(**c) for c in (jload(raw, []) or [])]
