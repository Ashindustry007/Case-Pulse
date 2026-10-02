"""FastAPI app (shared, FROZEN). Nobody registers routes here: every module in backend/app/api/ that exposes `router`
is auto-included. Startup fails if any API route lacks a role guard (deny-by-default, see auth.py).

Run: uv run uvicorn backend.app.main:app --reload --port 8000
"""
from __future__ import annotations

import importlib
import pkgutil

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from . import api as api_pkg
from .auth import public
from .config import settings
from .db import migrate

app = FastAPI(
    title="Case Pulse API",
    version="0.1.0",
    description="Cited case digestion for PI firms and their medical providers. Clio is read-only input.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted({settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"}),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_UNGUARDED: list[str] = []


def _include_routers() -> list[str]:
    loaded = []
    for mod in sorted(pkgutil.iter_modules(api_pkg.__path__), key=lambda m: m.name):
        module = importlib.import_module(f"{api_pkg.__name__}.{mod.name}")
        router = getattr(module, "router", None)
        if router is not None:
            # Check guards on the router's own APIRoutes (FastAPI >=0.14x wraps included routers lazily).
            _UNGUARDED.extend(f"{mod.name}: {sorted(r.methods)} {r.path}" for r in router.routes
                              if isinstance(r, APIRoute) and not _has_guard(r.dependant))
            app.include_router(router)
            loaded.append(mod.name)
    return loaded


def _has_guard(dependant) -> bool:
    for dep in dependant.dependencies:
        if hasattr(dep.call, "__role_guard__") or _has_guard(dep):
            return True
    return False


def _assert_all_routes_guarded() -> None:
    unguarded = _UNGUARDED + [f"app: {sorted(r.methods)} {r.path}" for r in app.routes
                              if isinstance(r, APIRoute) and not _has_guard(r.dependant)]
    if unguarded:
        raise RuntimeError("Routes without a role guard (add Depends(require_role(...)) or Depends(public)):\n  "
                           + "\n  ".join(unguarded))


LOADED_ROUTERS = _include_routers()


@app.get("/health", dependencies=[Depends(public)], tags=["meta"])
def health() -> dict:
    return {"ok": True, "routers": LOADED_ROUTERS}


_assert_all_routes_guarded()
migrate()
