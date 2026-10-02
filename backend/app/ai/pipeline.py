"""Digestion pipeline (F9): documents → OCR → index (local embeddings) → digests → extraction → brief.
Every stage is hash-gated, so re-running on an unchanged case makes ZERO LLM calls ($0.00).
Each run is recorded in `digest_runs` with per-stage LLM calls, tokens and cost (from `ai_runs`).

CLI:  make digest [MATTER=id]      make cache-demo [MATTER=id]
"""
from __future__ import annotations

import argparse
import json
import logging
import sqlite3
import sys
import threading
import time
from typing import Any, Callable

from ..db import connect, jdump, migrate, now_iso
from ..llm import max_run_id

log = logging.getLogger("casepulse.pipeline")
_lock = threading.Lock()


def _usage_since(db: sqlite3.Connection, run_id: int, matter_id: int) -> dict:
    r = db.execute("""SELECT COUNT(*) AS calls, COALESCE(SUM(input_tokens),0) AS inp, COALESCE(SUM(output_tokens),0)
                        AS outp, COALESCE(SUM(cost_usd),0) AS cost FROM ai_runs
                      WHERE id > ? AND (matter_id = ? OR matter_id IS NULL) AND cache_hit = 0 AND purpose != 'embed'""",
                   (run_id, matter_id)).fetchone()
    return {"llm_calls": r["calls"], "input_tokens": r["inp"], "output_tokens": r["outp"], "cost_usd": r["cost"]}


def run_pipeline(matter_id: int, *, trigger: str = "manual", clio: Any = None,
                 progress: Callable[[str], None] | None = None) -> dict:
    """Run every stage for one matter. `clio` = ClioClient (or test double); documents are skipped if None."""
    from ..documents.processor import process_matter_documents
    from ..rag.index import build_index
    from .brief import ensure_brief
    from .digest import digest_matter
    from .extract import extract_all
    from .ocr import ocr_pending_pages

    say = progress or (lambda m: log.info(m))
    with _lock, connect() as db:
        started = now_iso()
        start_id = max_run_id()
        records_seen = db.execute("SELECT COUNT(*) FROM records WHERE matter_id=? AND deleted_at IS NULL",
                                  (matter_id,)).fetchone()[0]
        cur = db.execute("INSERT INTO digest_runs(matter_id, trigger, started_at, records_seen) VALUES (?,?,?,?)",
                         (matter_id, trigger, started, records_seen))
        run_id = cur.lastrowid
        db.commit()
        stages: dict[str, dict] = {}

        def stage(name: str, fn: Callable[[], Any]) -> Any:
            before = max_run_id()
            t0 = time.monotonic()
            say(f"[{name}] …")
            try:
                res = fn()
            except Exception as e:  # noqa: BLE001 — a failing stage is recorded, later stages still run
                log.exception("stage %s failed", name)
                res = {"error": str(e)[:300]}
            db.commit()
            u = _usage_since(db, before, matter_id)
            stages[name] = {**(res if isinstance(res, dict) else {"result": res}), **u,
                            "seconds": round(time.monotonic() - t0, 1)}
            say(f"[{name}] {json.dumps(stages[name], default=str)}")
            return res

        if clio is not None:
            stage("documents", lambda: process_matter_documents(db, clio, matter_id))
        stage("ocr", lambda: ocr_pending_pages(db, matter_id))
        stage("index", lambda: build_index(db, matter_id))
        dig = stage("digest", lambda: digest_matter(db, matter_id))
        stage("extract", lambda: extract_all(db, matter_id))
        stage("brief", lambda: ensure_brief(db, matter_id))

        total = _usage_since(db, start_id, matter_id)
        changed = (dig or {}).get("digested", 0) if isinstance(dig, dict) else 0
        db.execute("""UPDATE digest_runs SET finished_at=?, records_changed=?, llm_calls=?, input_tokens=?,
                        output_tokens=?, cost_usd=?, cache_hit=?, stages=? WHERE id=?""",
                   (now_iso(), changed, total["llm_calls"], total["input_tokens"], total["output_tokens"],
                    round(total["cost_usd"], 6), int(total["llm_calls"] == 0), jdump(stages), run_id))
        db.commit()
        row = db.execute("SELECT * FROM digest_runs WHERE id=?", (run_id,)).fetchone()
        return dict(row)


def run_to_contract(row: dict | sqlite3.Row):
    from ..contracts import DigestRun

    d = dict(row)
    return DigestRun(id=d["id"], matter_id=d["matter_id"], trigger=d["trigger"], started_at=d["started_at"],
                     finished_at=d["finished_at"], records_seen=d["records_seen"],
                     records_changed=d["records_changed"], llm_calls=d["llm_calls"], input_tokens=d["input_tokens"],
                     output_tokens=d["output_tokens"], cost_usd=d["cost_usd"], cache_hit=bool(d["cache_hit"]),
                     stages=json.loads(d["stages"] or "{}"))


def _matters(db: sqlite3.Connection, only: int | None) -> list[int]:
    if only:
        return [only]
    return [r[0] for r in db.execute("SELECT DISTINCT matter_id FROM records")]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--matter", type=int)
    ap.add_argument("--cache-demo", action="store_true", help="run twice; the 2nd run must make 0 LLM calls")
    ap.add_argument("--no-documents", action="store_true", help="skip downloading documents from Clio")
    args = ap.parse_args()
    migrate()
    clio = None
    if not args.no_documents:
        from ..clio.client import ClioClient, connection_status

        if connection_status()["connected"]:
            clio = ClioClient()
        else:
            print("! Clio not connected — skipping document download")
    with connect() as db:
        ids = _matters(db, args.matter)
    if not ids:
        print("No synced matters — run `make sync` first")
        return 1
    for mid in ids:
        runs = 2 if args.cache_demo else 1
        for i in range(runs):
            row = run_pipeline(mid, trigger="cache_demo" if args.cache_demo else "manual", clio=clio)
            label = f"run {i + 1}/{runs}" if runs > 1 else "run"
            status = "cache hit" if row["cache_hit"] else f"{row['records_changed']} records digested"
            print(f"\n== matter {mid} {label}: {row['llm_calls']} LLM calls · ${row['cost_usd']:.4f} · {status} ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
