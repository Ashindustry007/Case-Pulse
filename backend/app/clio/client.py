"""Clio Manage API v4 client — READ-ONLY by construction.

Hackathon rule: "Read everything, write nothing." Any non-GET request to the Clio API raises ReadOnlyViolation.
The only POSTs this module makes go to Clio's OAuth token endpoint (/oauth/token), which exchanges/refreshes OUR
access token and never touches case data.

Features: OAuth code flow + refresh, 45 req/min token bucket (Clio allows 50/min), 429 Retry-After handling,
`meta.paging.next` pagination, nested `fields=` selection with automatic pruning of fields this account rejects.
"""
from __future__ import annotations

import json
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator
from urllib.parse import urlencode

import httpx

from ..config import settings
from ..db import connect, now_iso

API_PREFIX = "/api/v4"
REQUESTS_PER_MINUTE = 45


class ReadOnlyViolation(RuntimeError):
    """Raised if code attempts anything other than GET against the Clio API."""


class ClioNotConnected(RuntimeError):
    pass


class _TokenBucket:
    def __init__(self, per_minute: int) -> None:
        self.capacity = per_minute
        self.tokens = float(per_minute)
        self.rate = per_minute / 60.0
        self.updated = time.monotonic()
        self.lock = threading.Lock()

    def take(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
            time.sleep(wait)


_bucket = _TokenBucket(REQUESTS_PER_MINUTE)


# ------------------------------------------------------------------------------------------------------------------
# OAuth (our token only — never case data)
# ------------------------------------------------------------------------------------------------------------------
def authorize_url(state: str) -> str:
    q = urlencode({"response_type": "code", "client_id": settings.clio_client_id,
                   "redirect_uri": settings.clio_redirect_uri, "state": state})
    return f"{settings.clio_base_url}/oauth/authorize?{q}"


def _store_tokens(payload: dict, clio_user: dict | None = None) -> None:
    expires_at = None
    if payload.get("expires_in"):
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(payload["expires_in"]))).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
    with connect() as db:
        prev = db.execute("SELECT refresh_token, clio_user FROM clio_tokens WHERE id=1").fetchone()
        db.execute(
            """INSERT INTO clio_tokens(id, access_token, refresh_token, expires_at, clio_user, updated_at)
               VALUES (1,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET access_token=excluded.access_token,
                 refresh_token=COALESCE(excluded.refresh_token, clio_tokens.refresh_token),
                 expires_at=excluded.expires_at, clio_user=COALESCE(excluded.clio_user, clio_tokens.clio_user),
                 updated_at=excluded.updated_at""",
            (payload["access_token"], payload.get("refresh_token") or (prev["refresh_token"] if prev else None),
             expires_at, json.dumps(clio_user) if clio_user else None, now_iso()))


def exchange_code(code: str) -> None:
    """OAuth step 2: authorization code → access/refresh token (POST to the OAuth host, not the API)."""
    r = httpx.post(f"{settings.clio_base_url}/oauth/token", data={
        "client_id": settings.clio_client_id, "client_secret": settings.clio_client_secret,
        "grant_type": "authorization_code", "code": code, "redirect_uri": settings.clio_redirect_uri}, timeout=30)
    r.raise_for_status()
    _store_tokens(r.json())
    try:
        me = ClioClient().get("/users/who_am_i.json", fields="id,name,email").get("data")
        if me:
            _store_tokens({"access_token": r.json()["access_token"]}, clio_user=me)
    except Exception:  # noqa: BLE001 — identity is cosmetic
        pass


def _refresh() -> str:
    with connect() as db:
        row = db.execute("SELECT refresh_token FROM clio_tokens WHERE id=1").fetchone()
    if not row or not row["refresh_token"]:
        raise ClioNotConnected("No Clio refresh token — connect Clio again (/auth/clio/login)")
    r = httpx.post(f"{settings.clio_base_url}/oauth/token", data={
        "client_id": settings.clio_client_id, "client_secret": settings.clio_client_secret,
        "grant_type": "refresh_token", "refresh_token": row["refresh_token"]}, timeout=30)
    r.raise_for_status()
    _store_tokens(r.json())
    return r.json()["access_token"]


def connection_status() -> dict[str, Any]:
    with connect() as db:
        row = db.execute("SELECT clio_user, updated_at FROM clio_tokens WHERE id=1").fetchone()
    if not row:
        return {"connected": False, "clio_user": None}
    user = json.loads(row["clio_user"]) if row["clio_user"] else None
    return {"connected": True, "clio_user": (user or {}).get("name")}


# ------------------------------------------------------------------------------------------------------------------
# API client
# ------------------------------------------------------------------------------------------------------------------
_INVALID_FIELD = re.compile(r"(?:invalid|unknown|unpermitted)[^:]*field[s]?[^:]*:\s*([\w{}, .-]+)", re.I)


def _drop_field(fields: str, bad: str) -> str:
    """Remove a top-level field (and its nested {...} block) named `bad` from a fields= string."""
    bad = bad.strip().split("{")[0].strip()
    parts, depth, cur = [], 0, ""
    for ch in fields:
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        depth += ch == "{"
        depth -= ch == "}"
        cur += ch
    parts.append(cur)
    kept = [p for p in parts if p.split("{")[0].strip() != bad]
    if len(kept) == len(parts):  # maybe nested: drop "bad" inside braces
        return re.sub(rf"(?<=[{{,]){re.escape(bad)}(?=[,}}])", "", fields).replace(",,", ",").replace("{,", "{").replace(",}", "}")
    return ",".join(kept)


class ClioClient:
    def __init__(self, access_token: str | None = None) -> None:
        self._token = access_token
        self.requests_made = 0
        self._http = httpx.Client(base_url=settings.clio_base_url, timeout=60, follow_redirects=False)

    def _access_token(self) -> str:
        if self._token:
            return self._token
        with connect() as db:
            row = db.execute("SELECT access_token, expires_at FROM clio_tokens WHERE id=1").fetchone()
        if not row:
            raise ClioNotConnected("Clio is not connected — sign in as attorney and open /auth/clio/login")
        if row["expires_at"] and row["expires_at"] < now_iso():
            self._token = _refresh()
        else:
            self._token = row["access_token"]
        return self._token

    # The single choke point for every Clio API call.
    def request(self, method: str, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        if method.upper() != "GET":
            raise ReadOnlyViolation(f"Clio is read-only input: refusing {method.upper()} {path}")
        url = path if path.startswith("http") else f"{API_PREFIX}{path if path.startswith('/') else '/' + path}"
        for attempt in range(6):
            _bucket.take()
            self.requests_made += 1
            r = self._http.get(url, params=params, headers={"Authorization": f"Bearer {self._access_token()}"})
            if r.status_code == 401 and attempt == 0:
                self._token = _refresh()
                continue
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", "10")) + 0.5)
                continue
            if r.status_code >= 500:
                time.sleep(2 * (attempt + 1))
                continue
            return r
        return r

    def get(self, path: str, *, fields: str | None = None, **params: Any) -> dict:
        """GET a JSON resource. If Clio rejects a field in `fields`, it is pruned and the call retried."""
        p = {k: v for k, v in params.items() if v is not None}
        for _ in range(12):
            if fields:
                p["fields"] = fields
            r = self.request("GET", path, p)
            if r.status_code == 400 and fields:
                bad = self._bad_field(r, fields)
                if bad:
                    fields = _drop_field(fields, bad)
                    continue
            if r.status_code >= 400:
                raise httpx.HTTPStatusError(f"Clio GET {path} → {r.status_code}: {r.text[:300]}",
                                            request=r.request, response=r)
            return r.json()
        raise RuntimeError(f"Clio GET {path}: too many rejected fields")

    @staticmethod
    def _bad_field(r: httpx.Response, fields: str) -> str | None:
        try:
            msg = json.dumps(r.json())
        except ValueError:
            msg = r.text
        m = _INVALID_FIELD.search(msg)
        if m:
            return m.group(1).split(",")[0].strip()
        # Fall back: any top-level field name mentioned in the error message
        for name in re.findall(r"[a-z_]+", fields):
            if re.search(rf"\b{name}\b", msg) and name not in {"id", "etag"}:
                return name
        return None

    def paginate(self, path: str, *, fields: str | None = None, limit: int = 200, **params: Any) -> Iterator[dict]:
        """Yield every item across pages, following meta.paging.next."""
        page = self.get(path, fields=fields, limit=limit, **params)
        while True:
            yield from page.get("data") or []
            nxt = ((page.get("meta") or {}).get("paging") or {}).get("next")
            if not nxt:
                return
            r = self.request("GET", nxt)
            if r.status_code >= 400:
                raise httpx.HTTPStatusError(f"Clio paging → {r.status_code}", request=r.request, response=r)
            page = r.json()

    def download(self, document_id: int) -> tuple[bytes, str | None]:
        """Download a document's latest version (GET; follows Clio's redirect to file storage)."""
        r = self.request("GET", f"/documents/{document_id}/download")
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers["location"]
            r2 = httpx.get(loc, timeout=120, follow_redirects=True)  # signed storage URL, no Clio auth
            r2.raise_for_status()
            return r2.content, r2.headers.get("content-type")
        if r.status_code >= 400:
            raise httpx.HTTPStatusError(f"download {document_id} → {r.status_code}", request=r.request, response=r)
        return r.content, r.headers.get("content-type")
