"""Native-citation generation: case sources go to Claude as `search_result` blocks; Claude's `search_result_location`
citations are mapped back to exact spans (F3). Used by the Ask agent (streaming, tool use), the story brief and the
"since your last visit" delta summary.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterator
from typing import Any

from ..config import settings
from ..contracts import AnswerSegment, Citation, CitedSentence
from ..db import connect, jdump, now_iso
from ..llm import call_claude, last_cost, max_run_id, stream_claude
from .cite import ResultRegistry
from .search import Hit, hybrid_search

ASK_SYSTEM = """You are a careful legal assistant answering questions about ONE personal-injury case for the firm's
attorneys. Answer ONLY from the case sources provided (search results and tool results). Cite the sources for every
factual statement. If the sources do not contain the answer, say plainly that it is not in the case file — never guess
dates, amounts, diagnoses or coverage. Be concise: lead with the direct answer, then supporting detail. Use the
search_case tool to look for more evidence when the provided sources are not enough; use get_case_metrics for totals."""

TOOLS = [
    {"name": "search_case", "description": (
        "Search this case file (notes, emails, tasks, calendar, documents incl. OCR'd scans, bills, expenses, custom "
        "fields). Returns the most relevant passages as citable search results."),
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string", "description": "What to look for, in natural language"},
         "types": {"type": "array", "items": {"type": "string", "enum": [
             "note", "communication", "task", "calendar_entry", "document", "expense", "medical_record",
             "medical_bill", "damage", "custom_field", "contact", "matter_event", "bill", "time_entry"]},
                   "description": "Optional: restrict to these record types"},
         "date_from": {"type": "string", "description": "Optional ISO date lower bound"},
         "date_to": {"type": "string", "description": "Optional ISO date upper bound"}},
         "required": ["query"], "additionalProperties": False}},
    {"name": "get_case_metrics", "description": (
        "Exact computed totals from structured records (use instead of adding numbers yourself): "
        "medical_specials (all medical bills), firm_spend (expenses), provider_balances, upcoming_deadlines."),
     "input_schema": {"type": "object", "properties": {
         "kind": {"type": "string", "enum": ["medical_specials", "firm_spend", "provider_balances",
                                             "upcoming_deadlines"]}},
         "required": ["kind"], "additionalProperties": False}},
]


# ------------------------------------------------------------------------------------------------------------------
def block_segment(block: Any, registry: ResultRegistry, seg_id: str) -> AnswerSegment | None:
    if getattr(block, "type", None) != "text":
        return None
    cits: list[Citation] = []
    seen = set()
    for loc in getattr(block, "citations", None) or []:
        if getattr(loc, "type", "") != "search_result_location":
            continue
        c = registry.to_citation(loc)
        if c and (c.record_id, c.page, c.char_start) not in seen:
            seen.add((c.record_id, c.page, c.char_start))
            cits.append(c)
    return AnswerSegment(id=seg_id, text=block.text, citations=cits)


def segments_to_sentences(segments: list[AnswerSegment]) -> list[CitedSentence]:
    """Merge segments into lines/bullets; drop lines that carry no citation (F3: uncited text is not a fact)."""
    out: list[CitedSentence] = []
    cur_text, cur_cits = "", []

    def flush():
        nonlocal cur_text, cur_cits
        t = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", cur_text).strip()
        if t and cur_cits:
            uniq = {(c.record_id, c.page, c.char_start): c for c in cur_cits}
            out.append(CitedSentence(text=t, citations=list(uniq.values())))
        cur_text, cur_cits = "", []

    for s in segments:
        parts = s.text.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                flush()
            cur_text += part
            if part.strip():
                cur_cits.extend(s.citations)
    flush()
    return out


def cited_generation(purpose: str, matter_id: int, hits: list[Hit], instruction: str, *,
                     system: str, max_tokens: int = 4000, effort: str = "low") -> list[CitedSentence]:
    """One-shot generation grounded in `hits`, returning only cited sentences."""
    if not hits:
        return []
    reg = ResultRegistry()
    content = reg.blocks(hits) + [{"type": "text", "text": instruction}]
    msg = call_claude(purpose, settings.model_main, matter_id=matter_id, max_tokens=max_tokens,
                      output_config={"effort": effort}, system=system,
                      messages=[{"role": "user", "content": content}])
    segs = [s for i, b in enumerate(msg.content) if (s := block_segment(b, reg, f"s{i}"))]
    return segments_to_sentences(segs)


# ------------------------------------------------------------------------------------------------------------------
def _metrics(db: sqlite3.Connection, matter_id: int, kind: str) -> tuple[str, list[Hit]]:
    """Exact totals computed from structured records; returned with those records as citable search results."""
    from .search import hydrate

    if kind in ("medical_specials", "provider_balances"):
        rtype = "medical_bill"
    elif kind == "firm_spend":
        rtype = "expense"
    else:
        rtype = "task"
    if rtype == "expense":
        from ..ai.views import _firm_expenses

        rows = _firm_expenses(db, matter_id)
    else:
        rows = db.execute("SELECT id, meta FROM records WHERE matter_id=? AND type=? AND deleted_at IS NULL",
                          (matter_id, rtype)).fetchall()
    ids = [r["id"] for r in rows]
    chunk_ids = [c["id"] for c in db.execute(
        f"SELECT id FROM chunks WHERE record_id IN ({','.join('?' * len(ids))}) AND page_no IS NULL", ids)] if ids else []
    hits = list(hydrate(db, chunk_ids[:40]).values())
    metas = [json.loads(r["meta"] or "{}") for r in rows]
    if kind == "medical_specials":
        total = sum(m.get("amount") or 0 for m in metas)
        summary = f"Total of {len(metas)} medical bills in the file: ${total:,.2f}"
    elif kind == "provider_balances":
        by: dict[str, list[float]] = {}
        for m in metas:
            by.setdefault(m.get("provider_name") or "Unknown provider", [0.0, 0.0])
            by[m.get("provider_name") or "Unknown provider"][0] += m.get("amount") or 0
            by[m.get("provider_name") or "Unknown provider"][1] += m.get("balance") or 0
        summary = "; ".join(f"{p}: billed ${b:,.2f}, balance ${bal:,.2f}" for p, (b, bal) in by.items()) or "No bills"
    elif kind == "firm_spend":
        total = sum(m.get("amount") or 0 for m in metas)
        summary = (f"Total firm expenses on this matter ({len(metas)} entries): ${total:,.2f} "
                   "(client medical charges entered as expenses are excluded)")
    else:
        due = sorted((m.get("due_at") or "", m) for m in metas if m.get("status") not in ("complete", "completed"))
        summary = f"{len(due)} open tasks with due dates: " + "; ".join(d for d, _ in due[:10] if d)
    return summary, hits


def ask_stream(matter_id: int, user_id: int | None, question: str, history: list[dict]) -> Iterator[tuple[str, dict]]:
    """Agentic RAG with native citations. Yields (event, data) for SSE: status | segment | done | error."""
    start_id = max_run_id()
    reg = ResultRegistry()
    segments: list[AnswerSegment] = []
    with connect() as db:
        first_hits = hybrid_search(db, matter_id, question, k=10)
    messages: list[dict] = []
    for turn in history[-4:]:
        messages.append({"role": "user", "content": turn["question"]})
        messages.append({"role": "assistant", "content": turn["answer_text"]})
    messages.append({"role": "user", "content": reg.blocks(first_hits) + [
        {"type": "text", "text": f"Question about this case: {question}"}]})
    yield "status", {"message": "Reading the case file…"}
    try:
        for _ in range(5):
            with stream_claude("ask", settings.model_main, matter_id=matter_id, user_id=user_id, max_tokens=8000,
                               output_config={"effort": "medium"}, system=ASK_SYSTEM, tools=TOOLS,
                               messages=messages) as stream:
                for event in stream:
                    if event.type == "content_block_stop":
                        seg = block_segment(event.content_block, reg, f"s{len(segments) + 1}")
                        if seg and seg.text:
                            segments.append(seg)
                            yield "segment", seg.model_dump(mode="json")
                final = stream.get_final_message()
            if final.stop_reason == "refusal":
                yield "error", {"message": "The model declined to answer this question."}
                return
            if final.stop_reason != "tool_use":
                break
            messages.append({"role": "assistant", "content": final.content})
            results = []
            with connect() as db:
                for block in final.content:
                    if getattr(block, "type", "") != "tool_use":
                        continue
                    args = block.input or {}
                    if block.name == "search_case":
                        q = str(args.get("query", ""))[:300]
                        yield "status", {"message": f"Searching: {q}"}
                        hits = hybrid_search(db, matter_id, q, types=args.get("types") or None,
                                             date_from=args.get("date_from"), date_to=args.get("date_to"), k=8)
                        content = reg.blocks(hits) or [{"type": "text", "text": "No results found."}]
                    elif block.name == "get_case_metrics":
                        yield "status", {"message": "Computing totals…"}
                        summary, hits = _metrics(db, matter_id, str(args.get("kind")))
                        # A tool_result holding search_result blocks may contain ONLY search_result blocks, so the
                        # computed total travels in the first result's title; the records themselves stay citable.
                        content = reg.blocks(hits) or [{"type": "text", "text": summary}]
                        if hits:
                            content[0]["title"] = f"COMPUTED TOTAL — {summary} | {content[0]['title']}"
                    else:
                        content = [{"type": "text", "text": "Unknown tool"}]
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
            messages.append({"role": "user", "content": results})
    except Exception as e:  # noqa: BLE001
        yield "error", {"message": f"Ask failed: {e}"[:300]}
        return
    followups = suggest_followups(question, segments)
    cost = last_cost(matter_id, start_id)
    with connect() as db:
        db.execute("INSERT INTO qa_log(matter_id, user_id, question, answer, cost_usd, created_at) VALUES (?,?,?,?,?,?)",
                   (matter_id, user_id, question,
                    jdump({"segments": [s.model_dump(mode="json") for s in segments], "followups": followups}),
                    cost, now_iso()))
    yield "done", {"followups": followups, "cost_usd": round(cost, 4)}


def suggest_followups(question: str, segments: list[AnswerSegment]) -> list[str]:
    """Cheap heuristic follow-ups from what the answer cited (no extra LLM call)."""
    types = {c.source_type for s in segments for c in s.citations}
    ideas = []
    if "document" in types:
        ideas.append("Which documents support this, page by page?")
    if "medical_bill" in types or "medical_record" in types:
        ideas.append("What is each provider's outstanding balance?")
    if "communication" in types:
        ideas.append("What did the adjuster say most recently?")
    ideas.append("What changed on this case in the last 30 days?")
    return [i for i in ideas if i.lower() != question.lower()][:3]
