"""Smoke test: hit every endpoint as attorney and as provider, validate each response against contracts.py.
Requires the backend running (make backend). Creates two throwaway smoke users directly in the DB.

    uv run python scripts/smoke.py [--base http://localhost:8000]
"""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from pathlib import Path

import httpx
from pydantic import TypeAdapter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import contracts as C  # noqa: E402
from backend.app.auth import create_user  # noqa: E402
from backend.app.db import connect  # noqa: E402

FAIL: list[str] = []


def check(client: httpx.Client, method: str, path: str, model=None, *, expect: int = 200, body=None) -> object:
    r = client.request(method, path, json=body)
    label = f"{method} {path}"
    if r.status_code != expect:
        FAIL.append(f"{label} → {r.status_code} (expected {expect}) {r.text[:200]}")
        print(f"  ✗ {label} → {r.status_code}")
        return None
    data = None
    if model is not None:
        try:
            data = TypeAdapter(model).validate_python(r.json())
        except Exception as e:  # noqa: BLE001
            FAIL.append(f"{label} → contract violation: {e}"[:400])
            print(f"  ✗ {label} → contract violation")
            return None
    print(f"  ✓ {label}")
    return data


def login(base: str, email: str, password: str) -> httpx.Client:
    c = httpx.Client(base_url=base, timeout=120)
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    args = ap.parse_args()

    pw = secrets.token_urlsafe(12)
    with connect() as db:
        create_user(db, "smoke-attorney@casepulse.test", pw, "Smoke Attorney", "attorney")
        create_user(db, "smoke-provider@casepulse.test", pw, "Smoke Provider", "provider")

    print("attorney:")
    a = login(args.base, "smoke-attorney@casepulse.test", pw)
    check(a, "GET", "/api/auth/me", C.UserOut)
    check(a, "GET", "/api/sync/status", C.SyncStatus)
    matters = check(a, "GET", "/api/matters", list[C.MatterSummary]) or []
    if not matters:
        FAIL.append("no matters — run `make sync` first")
    else:
        m = matters[0].id
        check(a, "GET", f"/api/matters/{m}/overview", C.Overview)
        tl = check(a, "GET", f"/api/matters/{m}/timeline", C.Timeline)
        check(a, "GET", f"/api/matters/{m}/deadlines", C.Deadlines)
        check(a, "GET", f"/api/matters/{m}/costs", C.Costs)
        provs = check(a, "GET", f"/api/matters/{m}/providers", C.Providers)
        visit = check(a, "POST", f"/api/matters/{m}/visits", C.VisitResponse)
        from urllib.parse import urlencode
        since = "?" + urlencode({"since": visit.previous_visit_at}) if visit and visit.previous_visit_at else ""
        check(a, "GET", f"/api/matters/{m}/changes{since}", C.Changes)
        check(a, "GET", f"/api/matters/{m}/delta{since}", C.Delta)
        check(a, "GET", f"/api/matters/{m}/brief", C.Brief)
        check(a, "GET", f"/api/matters/{m}/suggested-questions", C.SuggestedQuestions)
        check(a, "GET", f"/api/matters/{m}/digest-runs", list[C.DigestRun])
        check(a, "GET", f"/api/ai-costs?matter_id={m}", C.AiCostReport)
        check(a, "GET", "/api/ai-costs/firm", C.FirmCostReport)
        if tl and tl.items:
            cit = tl.items[0].citations[0]
            check(a, "GET", f"/api/records/{cit.record_id}", C.SourceRecord)
        check(a, "POST", f"/api/matters/{m}/locate", C.LocateResult, body={"text": "primary injury"})
        # SSE ask: just verify the stream opens and ends with a done event
        with a.stream("POST", f"/api/matters/{m}/ask", json={"question": "What are the primary injuries?"}) as r:
            body = "".join(r.iter_text())
            ok = r.status_code == 200 and "event: done" in body
            print(("  ✓" if ok else "  ✗") + f" POST /api/matters/{m}/ask (SSE)")
            if not ok:
                FAIL.append(f"ask SSE → {r.status_code} {body[:200]}")
        if provs and provs.providers:
            pid = provs.providers[0].contact_id
            check(a, "GET", f"/api/matters/{m}/share-candidates?provider_contact_id={pid}", C.ShareCandidates)
            check(a, "POST", f"/api/matters/{m}/provider-draft", C.ProviderDraft,
                  body={"provider_contact_id": pid, "fields": ["status", "open_requests"]})
        check(a, "GET", f"/api/matters/{m}/shares", list[C.Grant])

    print("provider:")
    p = login(args.base, "smoke-provider@casepulse.test", pw)
    check(p, "GET", "/api/auth/me", C.UserOut)
    check(p, "GET", "/api/provider/cases", list[C.ProviderCaseSummary])
    if matters:
        m = matters[0].id
        for path in (f"/api/matters/{m}/overview", f"/api/matters/{m}/brief", "/api/records/note:1"):
            check(p, "GET", path, expect=403)
        check(p, "POST", f"/api/matters/{m}/ask", expect=403, body={"question": "x"})
    print("anonymous:")
    anon = httpx.Client(base_url=args.base, timeout=30)
    check(anon, "GET", "/api/matters", expect=401)

    print()
    if FAIL:
        print(f"SMOKE FAILED ({len(FAIL)}):")
        for f in FAIL:
            print("  -", f)
        return 1
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
