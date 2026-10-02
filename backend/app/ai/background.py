"""On-open freshness (F1): incremental Clio sync (time-boxed) + incremental digestion in the background."""
from __future__ import annotations

import logging
import threading

log = logging.getLogger("casepulse.background")
_running: set[int] = set()
_guard = threading.Lock()


def _refresh(matter_id: int, done: threading.Event, result: dict) -> None:
    try:
        from ..clio.client import ClioClient, connection_status
        from ..sync.engine import sync_matter
        from .pipeline import run_pipeline

        if not connection_status()["connected"]:
            return
        client = ClioClient()
        res = sync_matter(matter_id, client=client)
        result.update(res)
        done.set()
        if res.get("new") or res.get("changed") or res.get("removed"):
            run_pipeline(matter_id, trigger="on_open", clio=client)
    except Exception as e:  # noqa: BLE001
        log.warning("background refresh of %s failed: %s", matter_id, e)
    finally:
        done.set()
        with _guard:
            _running.discard(matter_id)


def refresh_on_open(matter_id: int, wait_seconds: float = 15.0) -> bool:
    """Start (or join) a refresh; wait up to `wait_seconds` for the sync part. Returns True if the sync finished."""
    with _guard:
        if matter_id in _running:
            return False
        _running.add(matter_id)
    done, result = threading.Event(), {}
    threading.Thread(target=_refresh, args=(matter_id, done, result), daemon=True).start()
    return done.wait(wait_seconds) and bool(result)
