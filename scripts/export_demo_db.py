"""Write data/casepulse.demo.db: the digested case, with credentials and logins removed, safe to commit.

    make export-demo            # reads data/casepulse.db (or DB_PATH), writes data/casepulse.demo.db

Removed: Clio OAuth tokens, app users + password hashes, share grants/invites/events, visit history, Ask history.
Kept: records, document pages, retrieval chunks + embeddings, digests, facts, briefs, provider requests, AI run costs.
A fresh clone gets the attorney login back with `make seed-attorney` and re-creates provider shares from the UI.
"""
from __future__ import annotations

import sys
from pathlib import Path

from backend.app import config
from backend.app.db import _open

WIPE = ["clio_tokens", "users", "invites", "share_grants", "share_policies", "share_events",
        "request_states", "matter_visits", "qa_log"]


def main() -> int:
    src_path = Path(config.settings.db_path)
    out = src_path.with_name("casepulse.demo.db")
    if not src_path.exists():
        print(f"no database at {src_path}", file=sys.stderr)
        return 1
    for p in (out, out.with_name(out.name + "-wal"), out.with_name(out.name + "-shm")):
        p.unlink(missing_ok=True)

    src = _open(src_path)
    # Secrets we must not find anywhere in the output file afterwards.
    secrets = [str(v) for row in src.execute("SELECT access_token, refresh_token FROM clio_tokens") for v in row if v]
    dst = _open(out)
    src.backup(dst)
    src.close()

    for table in WIPE:
        dst.execute(f"DELETE FROM {table}")
    dst.commit()
    dst.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    dst.execute("PRAGMA journal_mode=DELETE")   # one self-contained file, no -wal/-shm
    dst.execute("VACUUM")                        # rewrites the file so deleted rows are really gone
    left = {t: dst.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in WIPE}
    dst.close()
    for p in (out.with_name(out.name + "-wal"), out.with_name(out.name + "-shm")):
        p.unlink(missing_ok=True)

    blob = out.read_bytes()
    leaked = [i for i, s in enumerate(secrets) if s.encode() in blob]
    if any(left.values()) or leaked:
        out.unlink(missing_ok=True)
        print(f"REFUSING to keep {out}: rows left {left}, leaked token(s) {leaked}", file=sys.stderr)
        return 1
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB); wiped {', '.join(WIPE)}; no Clio token found in the file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
