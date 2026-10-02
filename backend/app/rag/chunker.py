"""Split source text into ~400-token chunks made of sentence UNITS with absolute char offsets.

Units are the citable atoms: Claude cites whole search_result text blocks, and each block is one unit, so a citation
maps back to an exact (char_start, char_end) span in the source text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TARGET_CHARS = 1600      # ≈ 400 tokens
MAX_UNIT_CHARS = 480     # longer "sentences" (tables, run-ons) are split at whitespace
_BOUNDARY = re.compile(r"(?<=[.!?;])\s+(?=[A-Z0-9\"'(\[])|\n+")


@dataclass
class Chunk:
    char_start: int
    char_end: int
    text: str
    units: list[tuple[int, int]]


def sentence_units(text: str) -> list[tuple[int, int]]:
    units: list[tuple[int, int]] = []
    pos = 0
    for m in list(_BOUNDARY.finditer(text)) + [None]:
        end = m.start() if m else len(text)
        _add_unit(text, pos, end, units)
        pos = m.end() if m else len(text)
    return units


def _add_unit(text: str, start: int, end: int, out: list[tuple[int, int]]) -> None:
    # trim whitespace
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if end - start < 2:
        return
    while end - start > MAX_UNIT_CHARS:
        cut = text.rfind(" ", start + MAX_UNIT_CHARS // 2, start + MAX_UNIT_CHARS)
        cut = cut if cut > start else start + MAX_UNIT_CHARS
        out.append((start, cut))
        start = cut
        while start < end and text[start].isspace():
            start += 1
    if end - start >= 2:
        out.append((start, end))


def chunk_text(text: str) -> list[Chunk]:
    units = sentence_units(text)
    chunks: list[Chunk] = []
    cur: list[tuple[int, int]] = []
    for u in units:
        if cur and (u[1] - cur[0][0]) > TARGET_CHARS:
            chunks.append(_mk(text, cur))
            cur = []
        cur.append(u)
    if cur:
        chunks.append(_mk(text, cur))
    return chunks


def _mk(text: str, units: list[tuple[int, int]]) -> Chunk:
    s, e = units[0][0], units[-1][1]
    return Chunk(char_start=s, char_end=e, text=text[s:e], units=list(units))
