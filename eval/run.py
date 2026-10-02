"""Ask-the-case eval: run the questions in eval/questions.yaml against a matter and measure
citation validity (every cited span must equal the source text at its offsets), cited share, latency and cost.

    uv run python eval/run.py --matter <id>        → prints a table and writes eval/results.md
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.db import connect  # noqa: E402
from backend.app.rag.answer import ask_stream  # noqa: E402


def citation_valid(db, c: dict) -> bool:
    if c.get("page"):
        row = db.execute("SELECT text FROM document_pages WHERE document_id=? AND page_no=?",
                         (c["record_id"], c["page"])).fetchone()
    else:
        row = db.execute("SELECT body_text AS text FROM records WHERE id=?", (c["record_id"],)).fetchone()
    if row is None:
        return False
    span = row["text"][c["char_start"]:c["char_end"]]
    norm = lambda s: " ".join(s.split())  # noqa: E731
    return norm(span) == norm(c["excerpt"]) or norm(c["excerpt"]) in norm(span) or norm(span) in norm(c["excerpt"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--matter", type=int, required=True)
    args = ap.parse_args()
    qs = yaml.safe_load(Path(__file__).with_name("questions.yaml").read_text())["questions"]
    rows, all_valid, all_cits = [], 0, 0
    for q in qs:
        t0 = time.time()
        segs, cost, err = [], 0.0, None
        for ev, data in ask_stream(args.matter, None, q, []):
            if ev == "segment":
                segs.append(data)
            elif ev == "done":
                cost = data["cost_usd"]
            elif ev == "error":
                err = data["message"]
        secs = time.time() - t0
        cits = [c for s in segs for c in s["citations"]]
        with connect() as db:
            valid = sum(citation_valid(db, c) for c in cits)
        text = "".join(s["text"] for s in segs)
        cited_chars = sum(len(s["text"]) for s in segs if s["citations"])
        all_valid += valid
        all_cits += len(cits)
        rows.append((q, len(cits), valid, cited_chars / max(1, len(text)), secs, cost, err, text))
        print(f"{'✓' if not err else '✗'} {q[:60]:<60} cits={len(cits):>2} valid={valid:>2} "
              f"cited={cited_chars / max(1, len(text)):.0%} {secs:5.1f}s ${cost:.3f}")
    total_cost = sum(r[5] for r in rows)
    summary = (f"\n{len(rows)} questions · citations valid {all_valid}/{all_cits} "
               f"({(all_valid / max(1, all_cits)):.0%}) · avg ${total_cost / max(1, len(rows)):.3f}/question · "
               f"avg {sum(r[4] for r in rows) / max(1, len(rows)):.1f}s")
    print(summary)
    out = ["# Ask-the-case eval", "", summary.strip(), "",
           "| Question | Citations | Valid | Cited share | Seconds | Cost |", "|---|---|---|---|---|---|"]
    out += [f"| {q} | {n} | {v} | {s:.0%} | {t:.1f} | ${c:.3f} |" for q, n, v, s, t, c, e, _ in rows]
    out += ["", "## Answers", ""] + [f"### {q}\n\n{text}\n" for q, *_, text in rows]
    Path(__file__).with_name("results.md").write_text("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
