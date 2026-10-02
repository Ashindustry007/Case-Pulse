"""[Dev 2] RBAC: role walls on EVERY route (auto-discovered, so Dev 1's routes are covered too), provider isolation."""
import importlib
import pkgutil
import re

from fastapi.routing import APIRoute

import backend.app.api
from backend.app.main import app  # noqa: F401
from backend.tests.dev2_support import EMAILS, MATTER, PROV_B, api, db_path, seeded, share  # noqa: F401


def _roles(dependant) -> set[str]:
    roles: set[str] = set()
    for d in dependant.dependencies:
        roles |= set(getattr(d.call, "__role_guard__", ()))
        roles |= _roles(d)
    return roles


def _routes(role: str) -> list[tuple[str, str]]:
    out = []
    # main.py wraps included routers lazily, so walk each api module's router directly (as main.py discovers them)
    for info in pkgutil.iter_modules(backend.app.api.__path__):
        router = getattr(importlib.import_module(f"backend.app.api.{info.name}"), "router", None)
        if router is None:
            continue
        for r in router.routes:
            if isinstance(r, APIRoute) and _roles(r.dependant) == {role}:
                out += [(m, re.sub(r"\{[^}]+\}", "1", r.path)) for m in sorted(r.methods - {"HEAD"})]
    assert out, f"no {role} routes discovered"
    return out


def _call(client, method, url):
    return client.request(method, url, json={} if method in ("POST", "PUT", "PATCH") else None)


def test_provider_is_forbidden_on_every_attorney_route(api):
    p = api("a")
    bad = [(m, u, s) for m, u in _routes("attorney") if (s := _call(p, m, u).status_code) != 403]
    assert not bad, bad


def test_attorney_is_forbidden_on_every_provider_route(api):
    a = api("attorney")
    bad = [(m, u, s) for m, u in _routes("provider") if (s := _call(a, m, u).status_code) != 403]
    assert not bad, bad


def test_anonymous_gets_401_everywhere_guarded(api):
    anon = api()
    bad = [(m, u, s) for m, u in _routes("attorney") + _routes("provider") if (s := _call(anon, m, u).status_code) != 401]
    assert not bad, bad


def test_provider_cannot_reach_another_providers_grant(api):
    att = api("attorney")
    gid, _ = share(att, fields=["status", "documents", "open_requests"], docs=["document:10"])
    b = api("b")
    assert b.get(f"/api/provider/cases/{gid}").status_code == 404
    assert b.get(f"/api/provider/cases/{gid}/documents/document:10").status_code == 404
    assert b.post("/api/provider/requests/req:1/complete").status_code == 404
    assert b.get("/api/provider/cases").json() == []


def test_revoked_grant_disappears_immediately(api):
    att = api("attorney")
    gid, _ = share(att, fields=["status", "documents"], docs=["document:10"])
    a = api("a")
    assert a.get(f"/api/provider/cases/{gid}").status_code == 200
    att.post(f"/api/shares/{gid}/revoke")
    assert a.get(f"/api/provider/cases/{gid}").status_code == 404
    assert a.get(f"/api/provider/cases/{gid}/documents/document:10").status_code == 404
    assert a.get("/api/provider/cases").json() == []


def test_document_outside_policy_is_404(api):
    att = api("attorney")
    gid, _ = share(att, fields=["documents"], docs=["document:10"])
    a = api("a")
    assert a.get(f"/api/provider/cases/{gid}/documents/document:11").status_code == 404
    gid2, _ = share(att, fields=["status"], docs=["document:10"])  # v2 drops the documents field
    assert a.get(f"/api/provider/cases/{gid2}/documents/document:10").status_code == 404
