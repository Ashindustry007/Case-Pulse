"""CLI: make sync [MATTER=<clio id>]   →   uv run python -m backend.app.sync [--matter ID] [--full] [--list]"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from ..clio.client import ClioClient, ClioNotConnected
from ..db import migrate
from .engine import list_clio_matters, sync_matter


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Pull matters from Clio (read-only) into data/casepulse.db")
    ap.add_argument("--matter", type=int, help="Clio matter id (default: every matter visible to the token)")
    ap.add_argument("--full", action="store_true", help="re-pull everything and detect deletions")
    ap.add_argument("--list", action="store_true", help="only list matters")
    args = ap.parse_args()
    migrate()
    client = ClioClient()
    try:
        matters = list_clio_matters(client)
    except ClioNotConnected as e:
        print(f"✗ {e}")
        return 1
    if args.list or not matters:
        for m in matters:
            print(f"{m['id']:>12}  {m.get('display_number')}  {m.get('status')}  {m.get('description')}")
        return 0 if matters else 1
    ids = [args.matter] if args.matter else [m["id"] for m in matters]
    for mid in ids:
        res = sync_matter(mid, full=True if args.full else None, client=client)
        print(f"\n== matter {mid} ({'full' if res['full'] else 'incremental'}) — {res['requests']} Clio GETs ==")
        for k, v in res["counts"].items():
            print(f"  {k:<18} {v}")
        print(f"  new={res['new']} changed={res['changed']} removed={res['removed']}")
        if res["errors"]:
            print("  errors:\n    " + "\n    ".join(f"{k}: {v}" for k, v in res["errors"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
