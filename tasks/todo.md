# Dev 2 — Product (Auth, Sharing, Frontend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Dev 2's half of Case Pulse (two-role auth + invites, share grants/policies/ProviderProjection backend, and the full Next.js attorney + provider frontend) so it merges into `main` alongside Dev 1's `ash` branch with zero conflicts in shared files.

**Architecture:** Backend work lives only in Dev 2-owned files (`backend/app/sharing/`, `backend/app/api/{auth_routes,shares,provider}.py`, `backend/tests/test_{rbac,sharing}.py` + one helper). Dev 1's schema is touched only through one read-only adapter (`sharing/sources.py`). Its assumptions are written down in an interface doc that Dev 1 acknowledges (Task 0), so drift at the checkpoint is a one-file fix. One builder (`build_sections` + `project`) produces both the real provider view and the composer preview, so preview == provider view by construction. The frontend is a Next.js 15 client-rendered app that calls FastAPI with cookie credentials, using types generated from `contracts.py`.

**Tech Stack:** Python 3.12 (uv), FastAPI, stdlib sqlite3, Pydantic v2, pytest + FastAPI TestClient · Next.js 15 (App Router, TS), Tailwind, shadcn/ui, Recharts, lucide-react, openapi-typescript, vitest.

**Spec:** `docs/PLAN.md` (source of truth) + `docs/workstreams/2-product-auth-sharing-frontend.md` (Dev 2 brief). Frozen contract: `backend/app/contracts.py`, `backend/db/schema.sql` on `origin/main` @ `cb1273a`.

## Global Constraints

- **Branch:** work on `raghu` (team convention: Dev 1 = `ash`; the PLAN's `feat/product` name is superseded by the per-person names). Rebase onto `origin/main` before starting and after every `main` commit.
- **Files you may create/edit:** `frontend/**`, `backend/app/sharing/**`, `backend/app/api/auth_routes.py`, `backend/app/api/shares.py`, `backend/app/api/provider.py`, `backend/tests/test_rbac.py`, `backend/tests/test_sharing.py`, `backend/tests/dev2_support.py`, `docs/workstreams/interface-dev1-dev2.md`, `tasks/**`, and Dev 2 fixtures listed in Task 9/10 (delete only).
- **Never edit:** `backend/app/{main,contracts,db,auth,llm,config,stubs}.py`, `backend/db/schema.sql`, `Makefile`, `pyproject.toml`, `uv.lock`, `.gitignore`, `.env.example`, `scripts/smoke.py`, any Dev 1 router/package/fixture. **Do not create `backend/tests/conftest.py`**: Dev 1 could create the same file and conflict. Test fixtures live in `backend/tests/dev2_support.py` and are imported explicitly.
- If a frozen file truly must change: tiny separate commit on `main`, push, tell Dev 1, rebase.
- **Routers:** `router = APIRouter(prefix=..., tags=[...], dependencies=[Depends(require_role("attorney"|"provider"))])`, or per-route `dependencies=[Depends(public)]`. Never register in `main.py` (auto-discovery). DB via `db: sqlite3.Connection = Depends(get_db)`; user via `user=Depends(current_user)`.
- **Helpers to reuse, never re-implement:** `now_iso()`, `jdump()`, `jload()` (db.py); `settings` (config.py; never `os.environ`); `create_user`, `issue_session`, `user_out`, `hash_password` (auth.py).
- **IDs:** Clio ids are INTEGER (`matter_id`, `provider_contact_id`); record ids are TEXT `"{type}:{clio_id}"` (e.g. `"document:10"`); request ids are TEXT. Path params: `{matter_id}`, `{grant_id}`, `{document_id}`, `{request_id}` exactly as in the stubs.
- **Timestamps:** ISO-8601 UTC `YYYY-MM-DDTHH:MM:SSZ` via `now_iso()`; dates `YYYY-MM-DD`.
- **Status codes:** role mismatch 403 (automatic from `require_role`); not signed in 401; provider touching a grant/doc/request that isn't theirs, is revoked, or has no policy → **404, never 403**; bad input 400; invalid state (revoked grant, used invite) 409/410.
- **Provider JSON:** `response_model_exclude_none=True` on every route returning `ProviderCase`/`ShareCandidates`. Unshared sections are absent, never "redacted".
- **API URL fields** (`photo_url`, `image_url`) are API-relative paths starting with `/`. The frontend prefixes `API_URL`.
- **Frontend:** API types only from generated `frontend/lib/api-types.ts`, re-exported through `frontend/lib/types.ts` (the single place to fix names after `make types`). Treat `null` and missing the same (`x != null`). Base URL is `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`). **Open the app at `http://localhost:3000`, not `127.0.0.1`**, because the `cp_session` cookie is host-scoped.
- Provider route group + `components/provider/**` must not import `components/attorney/**` (ESLint rule, Task 1).
- No case/client/provider names in app code (`grep -rni sapini frontend backend` → nothing). Synthetic test data uses generic names only.
- Never call Clio. Never write Dev 1 tables from app code (tests may seed them in a temp DB).
- Commit after every task (`feat(product): …`, `test(sharing): …`), push `raghu` at least every 30 min.

## Review Focus

1. **Dev 1 tables empty, partial or malformed** (before sync/digest, or a fact JSON that doesn't validate) → provider page, case list and share-candidates still return 200 with those sections omitted, never 500. Tests in Task 8.
2. **Date-only strings** (`"2026-09-28"`) rendered in a US timezone → the UI must show the same calendar date as the source, not the day before. Test in Task 1.
3. **Provider with a valid cookie hitting a revoked grant, another provider's grant/doc/request, or a doc not in the latest policy** → 404 every time, and the case list drops the grant immediately. Tests in Task 10.
4. **Invite misuse** (reused code, expired code, revoked grant, or an email that belongs to an attorney) → clear 4xx, and an attorney account is never converted or re-passworded. Tests in Task 2.
5. **SSE frames split across network chunks, or an `event: error` mid-stream** → the answer renders completely and the error is shown, never swallowed. Test in Task 1, handled in Task 7.

---

## Merge protocol (read once; applies all day)

- **Checkpoint (12:45):**
  ```bash
  git fetch origin
  git checkout -B integration origin/main
  git merge --no-edit origin/ash
  git merge --no-edit raghu
  uv run pytest -q
  make backend   # then `make smoke` in another terminal
  ```
  Fix drift on your own branch, never on `integration`. Throw `integration` away.
- **Freeze (14:45):** Dev 1 merges `ash` → `main` first. Then:
  ```bash
  git fetch origin && git rebase origin/main
  uv run pytest -q
  git checkout main && git merge --ff-only raghu && git push origin main
  make backend & make types
  ```
- The expected conflict surface is **zero** shared files. If git reports a conflict in a frozen file, stop and talk to Dev 1. Don't resolve it alone.
- `fixtures/` + `backend/app/stubs.py`: each dev deletes only their own fixtures. Whoever finishes last deletes `stubs.py` and the empty `fixtures/` (both devs deleting the same file merges cleanly).

---

### Task 0: Sync branch + lock the Dev 1 ↔ Dev 2 data interface

**Files:**
- Create: `docs/workstreams/interface-dev1-dev2.md` (committed to `main`)

**Interfaces:**
- Produces: the written agreement `sharing/sources.py` (Task 8) codes against.

- [ ] **Step 1: Rebase `raghu` onto the Phase 0 scaffold**

```bash
cd /Users/raghu/coding/SWANS-2026-Hackathon
git fetch origin
git checkout raghu
git rebase origin/main
git log --oneline -1   # expect: cb1273a contract: phase-0 scaffold (or newer)
uv sync && make migrate
```

- [ ] **Step 2: Write the interface doc**

Create `docs/workstreams/interface-dev1-dev2.md`:

````markdown
# Dev 1 ↔ Dev 2 data interface (read-only handoff through the DB)

Dev 2's sharing code reads Dev 1's tables ONLY through `backend/app/sharing/sources.py`. These are the exact
columns / JSON keys it relies on. Dev 1: please keep writing them in this shape (or tell Dev 2 before changing).
Anything missing is treated as "not available" → the provider section is omitted (never an error).

| Need | Table / column | Shape Dev 2 expects |
|---|---|---|
| Matter status / stage | `matters.status`, `matters.stage_name`, `matters.practice_area`, `matters.client_id` | status `closed` ⇒ heartbeat Closed |
| Stage bar | `matter_stages(name, practice_area, sort_order)` | ordered by `sort_order` |
| Patient initials | `contacts.name` via `matters.client_id` | "First Last" → "F. L." (full name never leaves the server) |
| Provider identity | `contacts(id, name, email)` | `id` = Clio contact id used as `provider_contact_id` everywhere |
| "Alive" / last activity | `records.occurred_at` (deleted_at IS NULL) | ISO date or datetime; future dates are ignored |
| Provider-safe movement | `digests.confidential`, `digests.provider_safe_summary` joined on `record_id` | safe ⇔ `confidential = 0 AND provider_safe_summary` non-empty |
| Provider's bills | `records` with `type='medical_bill'`, `meta` JSON | `meta.provider_contact_id` **INTEGER**, `meta.amount` number, `meta.balance` number\|null, `meta.lien` bool, optional `meta.description` |
| Documents | `records` with `type='document'`; page count from `document_pages` | `meta.file_path` = path **relative to `DATA_DIR`** (e.g. `files/document_10.pdf`) |
| Provider requests | `provider_requests` (schema as frozen) | `citations` JSON `[Citation]`; `source_addressed_to_provider` 0/1 |
| Coverage | latest `facts` row `kind='coverage'` | `value` = `contracts.Coverage` JSON |
| Case value | latest `facts` row `kind='worth'` | `value` = `contracts.WorthEstimate` or `contracts.NotFound` JSON |
| Treatment visits | `facts` rows `kind='treatment_visit'` (one row per visit) | `value` = `{"provider_contact_id": int\|null, "provider_name": str, "date": "YYYY-MM-DD", "description": str\|null}` |

API conventions both sides follow:
- `*_url` fields served by our API (`photo_url`, `image_url`) are API-relative paths starting with `/`.
- Provider-role routes return 404 (not 403) for anything outside the provider's own active grant.
- Dev 2 adds one attorney route in `api/shares.py`: `GET /api/matters/{matter_id}/requests?provider_contact_id=` →
  `list[ProviderRequest]` with full citations (attorney view of F7). No contract change.
- Nobody creates `backend/tests/conftest.py` without telling the other dev.
````

- [ ] **Step 3: Commit to `main`, push, notify Dev 1, return to `raghu`**

```bash
# untracked files (tasks/todo.md, the new doc) carry across checkouts untouched
git checkout main && git pull --ff-only origin main
git add docs/workstreams/interface-dev1-dev2.md
git commit -m "docs: Dev 1 ↔ Dev 2 data interface for sharing projection"
git push origin main
git checkout raghu && git rebase origin/main
```

Then message Dev 1: *"Pushed docs/workstreams/interface-dev1-dev2.md to main. It lists the exact columns/meta keys my provider projection reads (bill meta, document file_path, facts kinds coverage/worth/treatment_visit). Please confirm or tell me what differs."*

---

### Task 1: Frontend scaffold + core libs (PLAN 2.1)

**Files:**
- Create: `frontend/` (create-next-app), `frontend/lib/{api.ts,use-api.ts,sse.ts,types.ts,format.ts,citations.ts}`, `frontend/lib/{sse,format,citations}.test.ts`, `frontend/vitest.config.ts`, placeholder pages for every route in PLAN §5.1
- Modify: `frontend/app/globals.css` (append tokens), `frontend/eslint.config.mjs` (provider import rule), `frontend/package.json` (test script)

**Interfaces:**
- Produces:
  - `api<T>(path: string, opts?: {method?: string; json?: unknown; signal?: AbortSignal}): Promise<T>`, `ApiError {status, message}`, `API_URL`, `apiUrl(path)`
  - `useApi<T>(path: string | null): {data?: T; error?: ApiError; loading: boolean; reload(): void}`
  - `createSSEParser(onEvent)`, `postSSE(path, body, onEvent, signal?)`
  - `fmtDate`, `fmtDateTime`, `fmtMoney`, `fmtMoneyShort`, `daysAgo`, `parseISODate`
  - `chipLabel(c)`, `locateSpan(text, c): [before, mark, after]`, `uniqueCitations(list)`
  - type aliases in `lib/types.ts`

- [ ] **Step 1: Scaffold Next.js + deps**

```bash
cd /Users/raghu/coding/SWANS-2026-Hackathon
npx create-next-app@15 frontend --ts --tailwind --eslint --app --no-src-dir --import-alias "@/*" --use-npm --turbopack
cd frontend
npx shadcn@latest init -d
npx shadcn@latest add -y button card badge popover sheet tabs input label checkbox radio-group separator tooltip skeleton dropdown-menu sonner textarea table
npm i recharts lucide-react
npm i -D openapi-typescript vitest
npm pkg set scripts.test="vitest run"
```

Accept defaults for any remaining prompt. create-next-app won't run `git init` inside an existing repo.

- [ ] **Step 2: vitest config**

`frontend/vitest.config.ts`:
```ts
import path from "node:path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
  test: { environment: "node", include: ["lib/**/*.test.ts"] },
});
```

- [ ] **Step 3: Write failing tests for format, SSE, citations**

`frontend/lib/format.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { daysAgo, fmtDate, fmtMoney, fmtMoneyShort, parseISODate } from "./format";

describe("format", () => {
  it("keeps date-only strings on their calendar day in any timezone", () => {
    const d = parseISODate("2026-09-28");
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 8, 28]);
    expect(fmtDate("2026-09-28")).toBe("Sep 28, 2026");
  });
  it("formats money", () => {
    expect(fmtMoney(22140)).toBe("$22,140");
    expect(fmtMoneyShort(84200)).toBe("$84.2k");
    expect(fmtMoneyShort(150000)).toBe("$150k");
    expect(fmtMoneyShort(950)).toBe("$950");
  });
  it("counts whole days ago", () => {
    expect(daysAgo("2026-09-29", new Date(2026, 9, 2, 15))).toBe(3);
  });
  it("renders empty for missing dates", () => {
    expect(fmtDate(null)).toBe("");
  });
});
```

`frontend/lib/sse.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { createSSEParser, type SSEEvent } from "./sse";

describe("createSSEParser", () => {
  it("reassembles frames split across chunks", () => {
    const got: SSEEvent[] = [];
    const p = createSSEParser((e) => got.push(e));
    p.push('event: segment\ndata: {"id":"s1","te');
    p.push('xt":"Hello","citations":[]}\n');
    p.push("\nevent: done\ndata: {\"followups\":[]}\n\n");
    expect(got).toEqual([
      { event: "segment", data: { id: "s1", text: "Hello", citations: [] } },
      { event: "done", data: { followups: [] } },
    ]);
  });
  it("passes error events through and tolerates CRLF", () => {
    const got: SSEEvent[] = [];
    const p = createSSEParser((e) => got.push(e));
    p.push('event: error\r\ndata: {"message":"boom"}\r\n\r\n');
    expect(got).toEqual([{ event: "error", data: { message: "boom" } }]);
  });
});
```

`frontend/lib/citations.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { chipLabel, locateSpan, uniqueCitations } from "./citations";

const c = (o: Partial<Parameters<typeof locateSpan>[1]> = {}) => ({
  record_id: "note:12", source_type: "note" as const, title: "t", char_start: 4, char_end: 9, excerpt: "quick", page: null, ...o,
});

describe("citations", () => {
  it("labels chips by type, id and page", () => {
    expect(chipLabel(c())).toBe("n12");
    expect(chipLabel(c({ record_id: "document:4", source_type: "document", page: 112 }))).toBe("d4 p112");
  });
  it("splits text at the cited span", () => {
    expect(locateSpan("the quick fox", c())).toEqual(["the ", "quick", " fox"]);
  });
  it("falls back to searching the excerpt when offsets drift", () => {
    expect(locateSpan("a quick fox", c())).toEqual(["a ", "quick", " fox"]);
  });
  it("clamps out-of-range offsets", () => {
    expect(locateSpan("abc", c({ char_start: 10, char_end: 20, excerpt: "zzz" }))).toEqual(["abc", "", ""]);
  });
  it("dedupes citations", () => {
    expect(uniqueCitations([c(), c(), c({ char_start: 0 })])).toHaveLength(2);
  });
});
```

- [ ] **Step 4: Run, expect failure**

Run: `cd frontend && npm test`
Expected: FAIL, cannot resolve `./format`, `./sse`, `./citations`.

- [ ] **Step 5: Implement the libs**

`frontend/lib/format.ts`:
```ts
const DATE_ONLY = /^\d{4}-\d{2}-\d{2}$/;

/** Date-only strings are calendar dates, not UTC midnights: parse them in local time. */
export function parseISODate(iso: string): Date {
  if (DATE_ONLY.test(iso)) {
    const [y, m, d] = iso.split("-").map(Number);
    return new Date(y, m - 1, d);
  }
  return new Date(iso);
}

export function fmtDate(iso?: string | null): string {
  if (!iso) return "";
  return parseISODate(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function fmtDateTime(iso?: string | null): string {
  if (!iso) return "";
  return parseISODate(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

export function fmtMoney(n?: number | null): string {
  if (n == null) return "";
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function fmtMoneyShort(n: number): string {
  if (Math.abs(n) < 1000) return `$${Math.round(n)}`;
  const k = n / 1000;
  return `$${Number.isInteger(Math.round(k * 10) / 10) ? Math.round(k) : (Math.round(k * 10) / 10).toFixed(1)}k`;
}

export function daysAgo(iso: string, now: Date = new Date()): number {
  const d = parseISODate(iso);
  const a = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const b = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  return Math.round((b - a) / 86_400_000);
}

export const usd = (n: number) => `$${n.toFixed(2)}`;
```

`frontend/lib/sse.ts`:
```ts
import { API_URL, ApiError } from "./api";

export type SSEEvent = { event: string; data: unknown };

/** Incremental text/event-stream parser: push() raw chunks, get whole events. */
export function createSSEParser(onEvent: (e: SSEEvent) => void) {
  let buf = "";
  return {
    push(chunk: string) {
      buf += chunk.replace(/\r\n/g, "\n");
      let i: number;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const frame = buf.slice(0, i);
        buf = buf.slice(i + 2);
        let event = "message";
        const data: string[] = [];
        for (const line of frame.split("\n")) {
          if (line.startsWith("event:")) event = line.slice(6).trim();
          else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
        }
        if (!data.length) continue;
        const raw = data.join("\n");
        let parsed: unknown = raw;
        try { parsed = JSON.parse(raw); } catch { /* plain text payload */ }
        onEvent({ event, data: parsed });
      }
    },
  };
}

export async function postSSE(path: string, body: unknown, onEvent: (e: SSEEvent) => void, signal?: AbortSignal) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) throw new ApiError(res.status, `Stream failed (${res.status})`);
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  const parser = createSSEParser(onEvent);
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    parser.push(value);
  }
}
```

`frontend/lib/api.ts`:
```ts
export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** API-relative paths ("/api/...") → absolute URL; absolute URLs pass through. */
export const apiUrl = (path: string) => (path.startsWith("/") ? `${API_URL}${path}` : path);

export async function api<T>(
  path: string,
  opts: { method?: string; json?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const hasBody = opts.json !== undefined;
  const res = await fetch(apiUrl(path), {
    method: opts.method ?? (hasBody ? "POST" : "GET"),
    credentials: "include",
    headers: hasBody ? { "Content-Type": "application/json" } : undefined,
    body: hasBody ? JSON.stringify(opts.json) : undefined,
    signal: opts.signal,
  });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth/")) {
    window.location.assign(`/login?next=${encodeURIComponent(window.location.pathname)}`);
  }
  if (!res.ok) {
    let msg: unknown = res.statusText;
    try { msg = (await res.json()).detail ?? msg; } catch { /* non-JSON error */ }
    throw new ApiError(res.status, typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}
```

`frontend/lib/use-api.ts`:
```ts
"use client";
import { useEffect, useState } from "react";
import { api, ApiError } from "./api";

export function useApi<T>(path: string | null) {
  const [state, setState] = useState<{ data?: T; error?: ApiError; loading: boolean }>({ loading: !!path });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!path) { setState({ loading: false }); return; }
    const ctrl = new AbortController();
    setState((s) => ({ ...s, loading: true }));
    api<T>(path, { signal: ctrl.signal }).then(
      (data) => setState({ data, loading: false }),
      (error) => { if (!ctrl.signal.aborted) setState({ error, loading: false }); },
    );
    return () => ctrl.abort();
  }, [path, tick]);
  return { ...state, reload: () => setTick((t) => t + 1) };
}
```

`frontend/lib/citations.ts`:
```ts
import type { Citation } from "./types";

type CiteLike = Pick<Citation, "record_id" | "source_type" | "char_start" | "char_end" | "excerpt"> & { page?: number | null };

const PREFIX: Record<string, string> = {
  note: "n", communication: "c", task: "t", calendar_entry: "cal", document: "d", expense: "x", time_entry: "te",
  bill: "b", medical_record: "mr", medical_bill: "mb", damage: "dm", custom_field: "cf", matter_event: "ev", contact: "ct",
};

export function chipLabel(c: Pick<CiteLike, "record_id" | "source_type" | "page">): string {
  const id = c.record_id.includes(":") ? c.record_id.slice(c.record_id.indexOf(":") + 1) : c.record_id;
  const base = `${PREFIX[c.source_type] ?? "s"}${id}`;
  return c.page != null ? `${base} p${c.page}` : base;
}

/** [before, cited, after]. Uses offsets; if they don't match the excerpt, searches for the excerpt instead. */
export function locateSpan(text: string, c: CiteLike): [string, string, string] {
  let s = Math.max(0, Math.min(c.char_start, text.length));
  let e = Math.max(s, Math.min(c.char_end, text.length));
  if (text.slice(s, e) !== c.excerpt) {
    const found = text.indexOf(c.excerpt);
    if (found >= 0) { s = found; e = found + c.excerpt.length; }
  }
  return [text.slice(0, s), text.slice(s, e), text.slice(e)];
}

export function uniqueCitations<T extends CiteLike>(list: T[]): T[] {
  const seen = new Set<string>();
  return list.filter((c) => {
    const k = `${c.record_id}|${c.page ?? ""}|${c.char_start}|${c.char_end}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}
```

`frontend/lib/types.ts` (until `make types` runs, this file needs `api-types.ts`, so generate it now with the backend running):
```bash
# terminal A (repo root): make backend
# terminal B:
cd frontend && npx openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.ts
```
```ts
/** Single re-export point for generated API types. If `make types` renames a schema, fix it HERE only. */
import type { components } from "./api-types";

type S = components["schemas"];
export type Citation = S["Citation"];
export type NotFound = S["NotFound"];
export type Cited<T> = { value: T; citations: Citation[] };
export type MaybeFound<T> = Cited<T> | NotFound;
export const isNotFound = (x: unknown): x is NotFound =>
  !!x && typeof x === "object" && (x as NotFound).not_found === true;

export type UserOut = S["UserOut"];
export type Role = UserOut["role"];
export type MatterSummary = S["MatterSummary"];
export type Overview = S["Overview"];
export type Brief = S["Brief"];
export type Changes = S["Changes"];
export type Delta = S["Delta"];
export type VisitResponse = S["VisitResponse"];
export type DeadlineItem = S["DeadlineItem"];
export type Deadlines = S["Deadlines"];
export type Costs = S["Costs"];
export type Providers = S["Providers"];
export type ProviderSummary = S["ProviderSummary"];
export type Timeline = S["Timeline"];
export type SourceRecord = S["SourceRecord"];
export type DocumentPage = S["DocumentPage"];
export type AnswerSegment = S["AnswerSegment"];
export type LocateResult = S["LocateResult"];
export type SuggestedQuestions = S["SuggestedQuestions"];
export type ProviderDraft = S["ProviderDraft"];
export type DraftFlag = S["DraftFlag"];
export type DigestRun = S["DigestRun"];
export type AiCostReport = S["AiCostReport"];
export type FirmCostReport = S["FirmCostReport"];
export type ProviderCase = S["ProviderCase"];
export type ProviderCaseSummary = S["ProviderCaseSummary"];
export type ProviderRequest = S["ProviderRequest"];
export type ShareCandidates = S["ShareCandidates"];
export type Grant = S["Grant"];
export type ReleaseResult = S["ReleaseResult"];
export type ShareAudit = S["ShareAudit"];
export type ShareEvent = S["ShareEvent"];
export type ShareField = S["ReleaseRequest"]["fields"][number];
```

If `tsc` complains a name doesn't exist (FastAPI may emit `X-Input`/`X-Output` for models used both ways), run `grep -o '"[A-Za-z_]*-Output"' lib/api-types.ts | sort -u` and point the alias at the `-Output` variant.

- [ ] **Step 6: Run tests, expect pass**

Run: `cd frontend && npm test`
Expected: PASS (3 files, 13 tests).

- [ ] **Step 7: Design tokens + provider import rule**

Append to `frontend/app/globals.css`:
```css
/* Case Pulse tokens: calm legal navy, dense but readable */
:root {
  --primary: oklch(0.36 0.07 255);
  --primary-foreground: oklch(0.98 0 0);
  --ring: oklch(0.36 0.07 255);
}
.dark {
  --primary: oklch(0.78 0.08 255);
  --primary-foreground: oklch(0.2 0.03 255);
}
mark.cite-span { background: oklch(0.93 0.12 95); color: inherit; border-radius: 2px; padding: 0 1px; }
.cite-chip {
  font: 500 11px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
  padding: 0 4px; border-radius: 4px; color: var(--primary);
  background: color-mix(in oklch, var(--primary) 10%, transparent);
}
.cite-chip:hover { background: color-mix(in oklch, var(--primary) 20%, transparent); }
```

In `frontend/eslint.config.mjs`, add this object as the last element of the exported array:
```js
  {
    files: ["app/(provider)/**", "components/provider/**"],
    rules: {
      "no-restricted-imports": ["error", {
        patterns: [{ group: ["@/components/attorney", "@/components/attorney/*"],
                     message: "Provider code must not import attorney components." }],
      }],
    },
  },
```

- [ ] **Step 8: Placeholder routes (PLAN §5.1 tree)**

Create each file below with this body, swapping in the title:
```tsx
export default function Page() {
  return <div className="p-8 text-muted-foreground">TITLE (placeholder)</div>;
}
```
- `app/(auth)/login/page.tsx`: "Login"
- `app/(auth)/invite/[code]/page.tsx`: "Invite"
- `app/(attorney)/matters/page.tsx`: "Matters"
- `app/(attorney)/matters/[id]/page.tsx`: "Matter"
- `app/(attorney)/matters/[id]/share/page.tsx`: "Share composer"
- `app/(attorney)/costs/page.tsx`: "Firm AI costs"
- `app/(provider)/provider/cases/page.tsx`: "Provider cases"
- `app/(provider)/provider/cases/[grant]/page.tsx`: "Provider case"

Replace `app/page.tsx`:
```tsx
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/login");
}
```

Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Create empty dirs with `.gitkeep`: `components/citations/`, `components/attorney/`, `components/provider/`, `components/common/`.

- [ ] **Step 9: Verify boot + lint**

Run: `cd frontend && npm run lint && npm run build`
Expected: lint clean; build lists all 8 routes. Then `npm run dev` and open `http://localhost:3000/provider/cases` → placeholder renders.

- [ ] **Step 10: Commit**

```bash
git add frontend tasks/todo.md
git commit -m "feat(product): Next.js scaffold, api/sse/format/citation libs, design tokens"
git push -u origin raghu
```

---

### Task 2: Invites + accept endpoint, backend test harness (PLAN 2.2 backend)

`auth.py` already ships argon2, the JWT cookie, `require_role` and `seed-attorney`. Nothing to harden there. This task adds invites only.

**Files:**
- Create: `backend/tests/dev2_support.py`, `backend/app/sharing/invites.py`, `backend/app/sharing/events.py`, `backend/tests/test_sharing.py`
- Modify: `backend/app/api/auth_routes.py` (replace `accept_invite` stub)

**Interfaces:**
- Consumes: `create_user`, `issue_session`, `user_out` (auth.py); `connect`, `migrate`, `get_db`, `now_iso`, `jdump`, `jload` (db.py)
- Produces:
  - `events.log_event(db, grant_id: int, event: str, actor: sqlite3.Row | None, *, version: int | None = None, meta: dict | None = None) -> None`
  - `events.events_for(db, grant_id: int) -> list[ShareEvent]`
  - `invites.create_invite(db, email: str, grant_id: int) -> str` (plaintext code), `invites.invite_url(code) -> str`, `invites.deliver(email, url) -> None`, `invites.accept(db, code, password, name) -> sqlite3.Row` (raises `HTTPException`)
  - test support: fixtures `db_path`, `seeded`, `api`; constants `EMAILS`, `PASSWORD`, `MATTER`, `PROV_A`, `PROV_B`; helpers `seed(db, with_case_data=True)`, `days_ago(n)`, `cit(...)`, `share(...)`, `new_invite(db_path, email, contact)`

- [ ] **Step 1: Write the test support module**

`backend/tests/dev2_support.py`:
```python
"""[Dev 2] Test support for test_rbac.py / test_sharing.py.

Deliberately NOT conftest.py (that file would be shared with Dev 1). Import what you need:
    from backend.tests.dev2_support import api, db_path, seeded  # noqa: F401  (pytest fixtures)
Seeds Dev 1's tables in a TEMP database only, in the shapes agreed in docs/workstreams/interface-dev1-dev2.md.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.auth import create_user
from backend.app.db import connect, get_db, jdump, migrate, now_iso
from backend.app.main import app
from backend.app.sharing import sources

PASSWORD = "correct-horse-1"
EMAILS = {"attorney": "attorney@firm.test", "a": "provider-a@clinic.test", "b": "provider-b@clinic.test"}
MATTER, CLIENT, PROV_A, PROV_B = 1001, 100, 600, 601


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def cit(record_id: str, source_type: str = "note", excerpt: str = "source text") -> dict:
    return {"record_id": record_id, "source_type": source_type, "title": record_id,
            "char_start": 0, "char_end": len(excerpt), "excerpt": excerpt}


def seed(db, *, with_case_data: bool = True) -> dict[str, int]:
    now = now_iso()
    uid = {
        "attorney": create_user(db, EMAILS["attorney"], PASSWORD, "Firm Attorney", "attorney"),
        "a": create_user(db, EMAILS["a"], PASSWORD, "Provider A", "provider", PROV_A),
        "b": create_user(db, EMAILS["b"], PASSWORD, "Provider B", "provider", PROV_B),
    }
    db.execute("INSERT INTO matters(id, display_number, description, status, stage_name, practice_area, client_id, "
               "synced_at) VALUES (?,?,?,?,?,?,?,?)",
               (MATTER, "00001", "Test matter", "open", "Demand", "Personal Injury", CLIENT, now))
    for cid, name, email in ((CLIENT, "Pat Example", None), (PROV_A, "Provider A Clinic", EMAILS["a"]),
                             (PROV_B, "Provider B Clinic", EMAILS["b"])):
        db.execute("INSERT INTO contacts(id, name, type, email, synced_at) VALUES (?,?,?,?,?)",
                   (cid, name, "Company", email, now))
    for i, name in enumerate(("Intake", "Treatment", "Demand", "Settlement")):
        db.execute("INSERT INTO matter_stages(id, name, practice_area, sort_order) VALUES (?,?,?,?)",
                   (i + 1, name, "Personal Injury", i))
    if not with_case_data:
        return uid

    def rec(rid: str, type_: str, title: str, occurred: str, meta: dict | None = None) -> None:
        db.execute("INSERT INTO records(id, matter_id, type, title, body_text, occurred_at, meta, content_hash, "
                   "first_seen_at, last_changed_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (rid, MATTER, type_, title, title, occurred, jdump(meta or {}), rid, now, now))

    def digest(rid: str, confidential: int, safe: str | None) -> None:
        db.execute("INSERT INTO digests(record_id, matter_id, content_hash, confidential, provider_safe_summary, "
                   "created_at) VALUES (?,?,?,?,?,?)", (rid, MATTER, rid, confidential, safe, now))

    rec("communication:1", "communication", "ER records received", days_ago(10))
    digest("communication:1", 0, "ER records received")
    rec("note:2", "note", "Internal strategy discussion", days_ago(3))
    digest("note:2", 1, None)
    rec("medical_bill:30", "medical_bill", "Bill A", days_ago(40),
        {"provider_contact_id": PROV_A, "amount": 1200.0, "balance": 900.0, "lien": True})
    rec("medical_bill:31", "medical_bill", "Bill B", days_ago(35),
        {"provider_contact_id": PROV_B, "amount": 500.0, "balance": None, "lien": False})
    rec("document:10", "document", "Imaging report", days_ago(30), {"file_path": "files/report.pdf"})
    rec("document:11", "document", "Internal memo", days_ago(5), {"file_path": "files/memo.pdf"})
    db.execute("INSERT INTO document_pages(document_id, page_no, text, method) VALUES "
               "('document:10', 1, 'p1', 'text_layer'), ('document:10', 2, 'p2', 'text_layer')")
    for rid, prov, kind, desc, ago, channel, addressed, cits in (
        ("req:1", PROV_A, "records", "Records for recent visits", 7, "task", 0, [cit("task:40", "task")]),
        ("req:2", PROV_A, "bills", "Itemized bill", 2, "email", 1,
         [cit("communication:41", "communication", "Please send an itemized bill")]),
        ("req:3", PROV_B, "records", "Records for B", 4, "task", 0, [cit("task:42", "task")]),
    ):
        db.execute("INSERT INTO provider_requests(id, matter_id, provider_contact_id, kind, description, requested_at, "
                   "channel, source_addressed_to_provider, citations, input_hash, created_at) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (rid, MATTER, prov, kind, desc, days_ago(ago), channel, addressed, jdump(cits), rid, now))
    nf = lambda label: {"not_found": True, "label": label}  # noqa: E731
    facts = [
        ("coverage", {"carrier": {"value": "Acme Mutual", "citations": [cit("document:10", "document", "Acme")]},
                      "bi_per_person": {"value": "$100,000", "citations": [cit("document:10", "document", "100k")]},
                      "bi_per_accident": nf("BI per accident"), "um_uim": nf("UM/UIM"), "medpay": nf("MedPay"),
                      "confirmed": True}),
        ("worth", {"label": "Estimate", "low": 3000.0, "high": 6000.0, "currency": "USD", "method": "specials x band",
                   "assumptions": [{"label": "Bills total", "text": "$1,700", "not_found": False,
                                    "citations": [cit("medical_bill:30", "medical_bill", "Bill A")]}]}),
        ("treatment_visit", {"provider_contact_id": PROV_A, "provider_name": "Provider A Clinic",
                             "date": days_ago(80), "description": None}),
        ("treatment_visit", {"provider_contact_id": PROV_A, "provider_name": "Provider A Clinic",
                             "date": days_ago(20), "description": None}),
        ("treatment_visit", {"provider_contact_id": PROV_B, "provider_name": "Provider B Clinic",
                             "date": days_ago(40), "description": None}),
    ]
    for kind, value in facts:
        db.execute("INSERT INTO facts(matter_id, kind, value, citations, input_hash, created_at) VALUES (?,?,?,?,?,?)",
                   (MATTER, kind, jdump(value), "[]", kind, now))
    return uid


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    migrate(path)

    def _get_db():
        with connect(path) as conn:
            yield conn

    app.dependency_overrides[get_db] = _get_db
    monkeypatch.setattr(sources, "data_dir", lambda: tmp_path)
    (tmp_path / "files").mkdir()
    (tmp_path / "files" / "report.pdf").write_bytes(b"%PDF-1.4 test report")
    yield path
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seeded(db_path):
    with connect(db_path) as db:
        seed(db)
    return db_path


@pytest.fixture
def api(seeded):
    """Factory: api("attorney" | "a" | "b" | None) → TestClient with its own cookie jar, logged in."""

    def make(who: str | None = None) -> TestClient:
        client = TestClient(app)
        if who:
            r = client.post("/api/auth/login", json={"email": EMAILS[who], "password": PASSWORD})
            assert r.status_code == 200, r.text
        return client

    return make


def share(att: TestClient, *, contact: int = PROV_A, email: str = EMAILS["a"], fields=("status",), docs=(),
          detail: str = "confirmed", note: str | None = None) -> tuple[int, dict]:
    g = att.post("/api/shares", json={"matter_id": MATTER, "provider_contact_id": contact, "email": email})
    assert g.status_code == 200, g.text
    gid = g.json()["id"]
    r = att.post(f"/api/shares/{gid}/release", json={"fields": list(fields), "document_ids": list(docs),
                                                     "coverage_detail": detail, "status_note": note})
    assert r.status_code == 200, r.text
    return gid, r.json()


def new_invite(db_path, email: str, contact: int = PROV_A, *, revoked: bool = False) -> str:
    """Create a grant + invite directly (no release) and return the plaintext code."""
    from backend.app.sharing import invites

    with connect(db_path) as db:
        cur = db.execute("INSERT INTO share_grants(matter_id, provider_contact_id, email, created_at, revoked_at) "
                         "VALUES (?,?,?,?,?)", (MATTER, contact, email, now_iso(), now_iso() if revoked else None))
        return invites.create_invite(db, email, int(cur.lastrowid))
```

The module imports `backend.app.sharing.sources`, so create a stub now. Task 8 fills it in.

`backend/app/sharing/sources.py`:
```python
"""[Dev 2] Read-only adapter over Dev 1's tables (filled in by Task 8)."""
from __future__ import annotations

from pathlib import Path

from ..config import settings


def data_dir() -> Path:
    """Root that records.meta.file_path is relative to (patched in tests)."""
    return settings.data_dir
```

- [ ] **Step 2: Write failing invite tests**

`backend/tests/test_sharing.py`:
```python
"""[Dev 2] Sharing: invites, release/versioning, projection, events, request states (F5–F8)."""
from backend.app.db import connect
from backend.tests.dev2_support import (EMAILS, MATTER, PASSWORD, PROV_A, PROV_B, api, db_path,  # noqa: F401
                                        days_ago, new_invite, seeded, share)

# ---------------------------------------------------------------------------------------------------- invites (2.2)


def test_invite_accept_creates_provider_and_logs_in(api, seeded):
    code = new_invite(seeded, "new-provider@clinic.test")
    c = api()
    r = c.post(f"/api/auth/invite/{code}/accept", json={"password": "longpassword", "name": "New Provider"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "provider" and r.json()["provider_contact_id"] == PROV_A
    assert c.get("/api/auth/me").json()["email"] == "new-provider@clinic.test"
    with connect(seeded) as db:
        grant = db.execute("SELECT provider_user_id FROM share_grants WHERE email = ?",
                           ("new-provider@clinic.test",)).fetchone()
        assert grant["provider_user_id"] == r.json()["id"]
        assert db.execute("SELECT event FROM share_events").fetchone()["event"] == "invite_accepted"


def test_invite_cannot_be_reused(api, seeded):
    code = new_invite(seeded, "once@clinic.test")
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "longpassword"}).status_code == 200
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "otherpassword"}).status_code == 410


def test_expired_invite_rejected(api, seeded):
    code = new_invite(seeded, "late@clinic.test")
    with connect(seeded) as db:
        db.execute("UPDATE invites SET expires_at = '2000-01-01T00:00:00Z'")
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "longpassword"}).status_code == 410


def test_invite_for_revoked_grant_rejected(api, seeded):
    code = new_invite(seeded, "gone@clinic.test", revoked=True)
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "longpassword"}).status_code == 410


def test_invite_never_converts_an_attorney(api, seeded):
    code = new_invite(seeded, EMAILS["attorney"])
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "hijackpassword"}).status_code == 409
    # attorney password unchanged
    assert api().post("/api/auth/login", json={"email": EMAILS["attorney"], "password": PASSWORD}).status_code == 200


def test_unknown_invite_404(api):
    assert api().post("/api/auth/invite/nope/accept", json={"password": "longpassword"}).status_code == 404
```

- [ ] **Step 3: Run, expect failure**

Run: `uv run pytest backend/tests/test_sharing.py -q`
Expected: FAIL. `ImportError: cannot import name 'invites'` (in `new_invite`), or 501 from the stub.

- [ ] **Step 4: Implement events + invites + route**

`backend/app/sharing/events.py`:
```python
"""[Dev 2] Append-only share audit log (F8)."""
from __future__ import annotations

import sqlite3

from ..contracts import ShareEvent
from ..db import jdump, jload, now_iso


def log_event(db: sqlite3.Connection, grant_id: int, event: str, actor: sqlite3.Row | None, *,
              version: int | None = None, meta: dict | None = None) -> None:
    db.execute("INSERT INTO share_events(grant_id, policy_version, event, actor_user_id, actor_email, at, meta) "
               "VALUES (?,?,?,?,?,?,?)",
               (grant_id, version, event, actor["id"] if actor else None, actor["email"] if actor else None,
                now_iso(), jdump(meta or {})))


def events_for(db: sqlite3.Connection, grant_id: int) -> list[ShareEvent]:
    rows = db.execute("SELECT * FROM share_events WHERE grant_id = ? ORDER BY at, id", (grant_id,))
    return [ShareEvent(id=r["id"], grant_id=r["grant_id"], policy_version=r["policy_version"], event=r["event"],
                       actor_email=r["actor_email"], at=r["at"], meta=jload(r["meta"], {})) for r in rows]
```

`backend/app/sharing/invites.py`:
```python
"""[Dev 2] Provider invites: sha256-hashed single-use codes, 7-day expiry. Delivered via Resend if configured,
and ALWAYS printed to the server console (demo fallback)."""
from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException

from ..auth import create_user
from ..config import settings
from ..db import now_iso
from . import events

INVITE_DAYS = 7


def _hash(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def create_invite(db: sqlite3.Connection, email: str, grant_id: int) -> str:
    code = secrets.token_urlsafe(24)
    expires = (datetime.now(timezone.utc) + timedelta(days=INVITE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    db.execute("INSERT INTO invites(code_hash, email, grant_id, expires_at, created_at) VALUES (?,?,?,?,?)",
               (_hash(code), email, grant_id, expires, now_iso()))
    return code


def invite_url(code: str) -> str:
    return f"{settings.frontend_url}/invite/{code}"


def deliver(email: str, url: str) -> None:
    print(f"[invite] {email} → {url}", flush=True)
    if not (settings.resend_api_key and settings.invite_from_email):
        return
    try:
        httpx.post("https://api.resend.com/emails", timeout=10,
                   headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                   json={"from": settings.invite_from_email, "to": [email],
                         "subject": f"{settings.firm_name} shared a case update with you",
                         "html": f'<p>{settings.firm_name} shared a case with you on Case Pulse.</p>'
                                 f'<p><a href="{url}">Set your password and view the case</a> (link valid {INVITE_DAYS} days).</p>'}
                   ).raise_for_status()
    except httpx.HTTPError as e:
        print(f"[invite] email delivery failed ({e}); use the console link above", flush=True)


def accept(db: sqlite3.Connection, code: str, password: str, name: str | None) -> sqlite3.Row:
    inv = db.execute("SELECT * FROM invites WHERE code_hash = ?", (_hash(code),)).fetchone()
    if inv is None:
        raise HTTPException(404, "Invite not found")
    if inv["used_at"]:
        raise HTTPException(410, "This invite was already used. Sign in instead.")
    if inv["expires_at"] < now_iso():
        raise HTTPException(410, "This invite has expired. Ask the firm for a new link.")
    grant = db.execute("SELECT * FROM share_grants WHERE id = ?", (inv["grant_id"],)).fetchone()
    if grant is None or grant["revoked_at"]:
        raise HTTPException(410, "This share is no longer active.")
    existing = db.execute("SELECT role FROM users WHERE email = ?", (inv["email"],)).fetchone()
    if existing and existing["role"] != "provider":
        raise HTTPException(409, "This email belongs to a firm account.")
    uid = create_user(db, inv["email"], password, name, "provider", grant["provider_contact_id"])
    db.execute("UPDATE share_grants SET provider_user_id = ? WHERE id = ?", (uid, grant["id"]))
    db.execute("UPDATE invites SET used_at = ? WHERE code_hash = ?", (now_iso(), inv["code_hash"]))
    user = db.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    latest = db.execute("SELECT MAX(version) AS v FROM share_policies WHERE grant_id = ?", (grant["id"],)).fetchone()
    events.log_event(db, grant["id"], "invite_accepted", user, version=latest["v"])
    return user
```

In `backend/app/api/auth_routes.py`, add `from ..sharing import invites`, then replace the stub `accept_invite` with:
```python
@router.post("/invite/{code}/accept", dependencies=[Depends(public)], response_model=UserOut)
def accept_invite(code: str, body: InviteAcceptRequest, response: Response, db: sqlite3.Connection = Depends(get_db)):
    user = invites.accept(db, code, body.password, body.name)
    issue_session(response, user["id"], user["role"])
    return user_out(user)
```
Also update the module docstring to `"""[Dev 2] Auth routes: login/logout/me + provider invite acceptance."""`.

- [ ] **Step 5: Run, expect pass**

Run: `uv run pytest backend/tests/test_sharing.py -q`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/sharing backend/app/api/auth_routes.py backend/tests/dev2_support.py backend/tests/test_sharing.py
git commit -m "feat(product): provider invites (hashed, single-use, 7d) + accept endpoint"
```

---

### Task 3: Frontend auth: route guard, login, invite, sign-out, layouts (PLAN 2.2 frontend)

**Files:**
- Create: `frontend/lib/route-guard.ts`, `frontend/lib/route-guard.test.ts`, `frontend/middleware.ts`, `frontend/components/common/SignOutButton.tsx`, `frontend/components/common/states.tsx`, `frontend/app/(attorney)/layout.tsx`, `frontend/app/(provider)/layout.tsx`
- Modify: `frontend/app/(auth)/login/page.tsx`, `frontend/app/(auth)/invite/[code]/page.tsx`, `frontend/app/layout.tsx`

**Interfaces:**
- Consumes: `api`, `UserOut`
- Produces: `roleFromToken(token?) -> Role | null`, `routeDecision(pathname, role) -> string | null` (redirect target), `HOME: Record<Role,string>`, `<SignOutButton/>`, `<Loading/>`, `<ErrorNote error/>`, `<NotFoundText/>`

- [ ] **Step 1: Failing tests**

`frontend/lib/route-guard.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { roleFromToken, routeDecision } from "./route-guard";

const tok = (payload: object) =>
  `x.${Buffer.from(JSON.stringify(payload)).toString("base64url")}.y`;

describe("roleFromToken", () => {
  it("reads the role claim", () => {
    expect(roleFromToken(tok({ sub: "1", role: "provider", exp: Date.now() / 1000 + 60 }))).toBe("provider");
  });
  it("rejects expired, malformed and unknown roles", () => {
    expect(roleFromToken(tok({ role: "attorney", exp: 1 }))).toBeNull();
    expect(roleFromToken("garbage")).toBeNull();
    expect(roleFromToken(tok({ role: "admin" }))).toBeNull();
    expect(roleFromToken(undefined)).toBeNull();
  });
});

describe("routeDecision", () => {
  it("sends anonymous users to login with next", () => {
    expect(routeDecision("/matters/1", null)).toBe("/login?next=%2Fmatters%2F1");
    expect(routeDecision("/", null)).toBe("/login");
  });
  it("keeps each role in its own area", () => {
    expect(routeDecision("/matters", "provider")).toBe("/provider/cases");
    expect(routeDecision("/costs", "provider")).toBe("/provider/cases");
    expect(routeDecision("/provider/cases/1", "attorney")).toBe("/matters");
    expect(routeDecision("/login", "attorney")).toBe("/matters");
  });
  it("allows the right role through", () => {
    expect(routeDecision("/matters/1/share", "attorney")).toBeNull();
    expect(routeDecision("/provider/cases", "provider")).toBeNull();
    expect(routeDecision("/login", null)).toBeNull();
  });
});
```

- [ ] **Step 2: Run, expect failure**

Run: `cd frontend && npm test -- route-guard`
Expected: FAIL, cannot resolve `./route-guard`.

- [ ] **Step 3: Implement guard + middleware**

`frontend/lib/route-guard.ts`:
```ts
/** UX-only routing by role. The backend is the authority; this just avoids showing the wrong app. */
export type GuardRole = "attorney" | "provider";
export const HOME: Record<GuardRole, string> = { attorney: "/matters", provider: "/provider/cases" };

export function roleFromToken(token?: string): GuardRole | null {
  const part = token?.split(".")[1];
  if (!part) return null;
  try {
    const b64 = part.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(part.length / 4) * 4, "=");
    const claims = JSON.parse(atob(b64));
    if (claims.exp && claims.exp * 1000 < Date.now()) return null;
    return claims.role === "attorney" || claims.role === "provider" ? claims.role : null;
  } catch {
    return null;
  }
}

export function routeDecision(pathname: string, role: GuardRole | null): string | null {
  const attorneyArea = pathname.startsWith("/matters") || pathname.startsWith("/costs");
  const providerArea = pathname.startsWith("/provider");
  const entry = pathname === "/" || pathname === "/login";
  if (!role) {
    if (pathname === "/") return "/login";
    return attorneyArea || providerArea ? `/login?next=${encodeURIComponent(pathname)}` : null;
  }
  if (entry || (role === "provider" && attorneyArea) || (role === "attorney" && providerArea)) return HOME[role];
  return null;
}
```

`frontend/middleware.ts`:
```ts
import { NextResponse, type NextRequest } from "next/server";
import { roleFromToken, routeDecision } from "@/lib/route-guard";

export function middleware(req: NextRequest) {
  const target = routeDecision(req.nextUrl.pathname, roleFromToken(req.cookies.get("cp_session")?.value));
  return target ? NextResponse.redirect(new URL(target, req.url)) : NextResponse.next();
}

export const config = { matcher: ["/", "/login", "/matters/:path*", "/costs/:path*", "/provider/:path*"] };
```

- [ ] **Step 4: Run, expect pass**

Run: `cd frontend && npm test`
Expected: all pass.

- [ ] **Step 5: Shared UI states + sign-out**

`frontend/components/common/states.tsx`:
```tsx
import { Skeleton } from "@/components/ui/skeleton";

export function Loading({ lines = 3 }: { lines?: number }) {
  return <div className="space-y-2">{Array.from({ length: lines }, (_, i) => <Skeleton key={i} className="h-4 w-full" />)}</div>;
}

export function ErrorNote({ error }: { error?: { message: string } | null }) {
  if (!error) return null;
  return <p className="text-sm text-destructive">Couldn&apos;t load: {error.message}</p>;
}

export function NotFoundText() {
  return <span className="italic text-muted-foreground">not found in file</span>;
}
```

`frontend/components/common/SignOutButton.tsx`:
```tsx
"use client";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export function SignOutButton() {
  return (
    <Button variant="ghost" size="sm" onClick={async () => { await api("/api/auth/logout", { method: "POST" }); window.location.assign("/login"); }}>
      <LogOut className="mr-1 h-4 w-4" /> Sign out
    </Button>
  );
}
```

- [ ] **Step 6: Login + invite pages**

`frontend/app/(auth)/login/page.tsx`:
```tsx
"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { HOME } from "@/lib/route-guard";
import type { UserOut } from "@/lib/types";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const user = await api<UserOut>("/api/auth/login", { json: { email, password } });
      const next = new URLSearchParams(window.location.search).get("next");
      const home = HOME[user.role];
      window.location.assign(next && next.startsWith(home) ? next : home);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Wrong email or password." : String(err));
      setBusy(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-muted/40 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader><CardTitle>◉ Case Pulse</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1"><Label htmlFor="email">Email</Label>
              <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
            <div className="space-y-1"><Label htmlFor="password">Password</Label>
              <Input id="password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</Button>
            <p className="text-xs text-muted-foreground">First time? Use the invite link from your email.</p>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
```

`frontend/app/(auth)/invite/[code]/page.tsx`:
```tsx
"use client";
import { use, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import type { UserOut } from "@/lib/types";

export default function InvitePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) { setError("Use at least 8 characters."); return; }
    try {
      await api<UserOut>(`/api/auth/invite/${encodeURIComponent(code)}/accept`, { json: { password, name: name || null } });
      window.location.assign("/provider/cases");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err));
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-muted/40 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader><CardTitle>Set up your Case Pulse access</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-4">
            <div className="space-y-1"><Label htmlFor="name">Your name</Label>
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} /></div>
            <div className="space-y-1"><Label htmlFor="pw">Choose a password</Label>
              <Input id="pw" type="password" autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full">Continue</Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
```

- [ ] **Step 7: Layouts**

In `frontend/app/layout.tsx`, set `metadata = { title: "Case Pulse", description: "Cited case dashboard" }` and render `<Toaster richColors />` (from `@/components/ui/sonner`) inside `<body>` after `{children}`.

`frontend/app/(provider)/layout.tsx`:
```tsx
import { SignOutButton } from "@/components/common/SignOutButton";

export default function ProviderLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-muted/30">
      <header className="flex items-center justify-between border-b bg-background px-4 py-2">
        <span className="font-semibold">◉ Case Pulse</span>
        <SignOutButton />
      </header>
      <main className="mx-auto max-w-3xl p-3 sm:p-6">{children}</main>
    </div>
  );
}
```

`frontend/app/(attorney)/layout.tsx` (SourceDrawerProvider is added in Task 4):
```tsx
import Link from "next/link";
import { SignOutButton } from "@/components/common/SignOutButton";

export default function AttorneyLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <header className="flex items-center gap-4 border-b px-4 py-2">
        <Link href="/matters" className="font-semibold">◉ Case Pulse</Link>
        <Link href="/matters" className="text-sm text-muted-foreground hover:text-foreground">Matters</Link>
        <Link href="/costs" className="text-sm text-muted-foreground hover:text-foreground">AI costs</Link>
        <span className="ml-auto text-xs text-muted-foreground">Attorney</span>
        <SignOutButton />
      </header>
      {children}
    </div>
  );
}
```

- [ ] **Step 8: Manual verification (backend running with stubs)**

```bash
# .env must have ATTORNEY_PASSWORD; then:
make seed-attorney && make backend      # terminal A
cd frontend && npm run dev               # terminal B
```
1. `http://localhost:3000/matters` while signed out → redirected to `/login?next=%2Fmatters`.
2. Sign in as the attorney → lands on `/matters`. Visit `/provider/cases` → bounced to `/matters`.
3. Sign out → `/login`.
4. Invite flow: `uv run python -c "from backend.tests.dev2_support import new_invite; print(new_invite(None, 'p@clinic.test'))"` (`None` = the default `DB_PATH`) prints a code. Open `/invite/<code>`, set a password → lands on `/provider/cases`. Visit `/matters` → bounced back.

- [ ] **Step 9: Commit**

```bash
git add frontend
git commit -m "feat(product): login, invite accept, role routing middleware, sign-out"
```

---

### Task 4: Citations UI: chip, popover, Source Drawer, `<Cited>` (PLAN 2.3, F3)

**Files:**
- Create: `frontend/components/citations/{SourceDrawer.tsx,CitationChip.tsx,Cited.tsx}`
- Modify: `frontend/app/(attorney)/layout.tsx` (wrap in provider)

**Interfaces:**
- Consumes: `chipLabel`, `locateSpan`, `useApi`, `apiUrl`, `fmtDate`, `isNotFound`
- Produces: `<SourceDrawerProvider>`, `useSourceDrawer(): {open(list: Citation[], index?: number): void}`, `<CitationChip citation siblings?/>`, `<Chips citations/>`, `<Cited value render?/>`

- [ ] **Step 1: Source Drawer**

`frontend/components/citations/SourceDrawer.tsx`:
```tsx
"use client";
import { ChevronLeft, ChevronRight, ExternalLink } from "lucide-react";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { ErrorNote, Loading } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { apiUrl } from "@/lib/api";
import { locateSpan } from "@/lib/citations";
import { fmtDate } from "@/lib/format";
import type { Citation, DocumentPage, SourceRecord } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type Ctx = { open: (list: Citation[], index?: number) => void };
const SourceCtx = createContext<Ctx>({ open: () => {} });
export const useSourceDrawer = () => useContext(SourceCtx);

export function SourceDrawerProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<{ list: Citation[]; i: number } | null>(null);
  const cite = state?.list[state.i];
  return (
    <SourceCtx.Provider value={{ open: (list, i = 0) => setState({ list, i }) }}>
      {children}
      <Sheet open={!!state} onOpenChange={(o) => !o && setState(null)}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-3xl">
          {state && cite && (
            <SourceView
              key={`${state.i}-${cite.record_id}`}
              citation={cite}
              pos={state.i}
              total={state.list.length}
              go={(d) => setState({ ...state, i: (state.i + d + state.list.length) % state.list.length })}
            />
          )}
        </SheetContent>
      </Sheet>
    </SourceCtx.Provider>
  );
}

function SourceView({ citation, pos, total, go }: { citation: Citation; pos: number; total: number; go: (d: number) => void }) {
  const isPage = citation.page != null;
  const id = encodeURIComponent(citation.record_id);
  const record = useApi<SourceRecord>(`/api/records/${id}`);
  const page = useApi<DocumentPage>(isPage ? `/api/documents/${id}/pages/${citation.page}` : null);
  const markRef = useRef<HTMLElement>(null);
  const text = isPage ? page.data?.text : record.data?.body_text;
  useEffect(() => { markRef.current?.scrollIntoView({ block: "center" }); }, [text]);
  const [before, mark, after] = locateSpan(text ?? "", citation);
  const clioUrl = citation.clio_url ?? record.data?.clio_url;
  const r = record.data;

  return (
    <div className="space-y-3">
      <SheetHeader>
        <SheetTitle className="text-base">
          📄 {citation.title}
          {isPage && ` · page ${citation.page}${page.data ? `/${page.data.page_count}` : ""}`}
        </SheetTitle>
        <p className="text-xs text-muted-foreground">
          {citation.source_type.replace(/_/g, " ")}
          {(citation.date ?? r?.occurred_at) && ` · ${fmtDate(citation.date ?? r?.occurred_at)}`}
          {(citation.author ?? r?.author) && ` · by ${citation.author ?? r?.author}`}
        </p>
      </SheetHeader>
      <div className="flex items-center gap-2">
        {total > 1 && (
          <>
            <Button variant="outline" size="sm" onClick={() => go(-1)}><ChevronLeft className="h-4 w-4" /> prev cite</Button>
            <span className="text-xs text-muted-foreground">{pos + 1} / {total}</span>
            <Button variant="outline" size="sm" onClick={() => go(1)}>next cite <ChevronRight className="h-4 w-4" /></Button>
          </>
        )}
        {clioUrl && (
          <Button asChild variant="link" size="sm" className="ml-auto">
            <a href={clioUrl} target="_blank" rel="noreferrer">Open in Clio <ExternalLink className="ml-1 h-3 w-3" /></a>
          </Button>
        )}
      </div>
      <ErrorNote error={isPage ? page.error : record.error} />
      {text == null ? <Loading lines={8} /> : (
        <div className={isPage && page.data?.image_url ? "grid grid-cols-2 gap-3" : ""}>
          {isPage && page.data?.image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={apiUrl(page.data.image_url)} alt={`Page ${citation.page}`} className="w-full rounded border" />
          )}
          <pre className="whitespace-pre-wrap rounded border bg-muted/30 p-3 font-sans text-sm leading-relaxed">
            {before}<mark ref={markRef} className="cite-span">{mark}</mark>{after}
          </pre>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Chip + `<Cited>`**

`frontend/components/citations/CitationChip.tsx`:
```tsx
"use client";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { chipLabel } from "@/lib/citations";
import { fmtDate } from "@/lib/format";
import type { Citation } from "@/lib/types";
import { useSourceDrawer } from "./SourceDrawer";

export function CitationChip({ citation, siblings }: { citation: Citation; siblings?: Citation[] }) {
  const { open } = useSourceDrawer();
  const list = siblings ?? [citation];
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button type="button" className="cite-chip" aria-label={`Source ${chipLabel(citation)}`}>[{chipLabel(citation)}]</button>
      </PopoverTrigger>
      <PopoverContent className="w-96 text-sm">
        <p className="text-xs text-muted-foreground">
          {citation.source_type.replace(/_/g, " ")} · {citation.title}
          {citation.author && ` · ${citation.author}`}
          {citation.date && ` · ${fmtDate(citation.date)}`}
          {citation.page != null && ` · p.${citation.page}`}
        </p>
        <blockquote className="mt-2 border-l-2 pl-3 italic">“{citation.excerpt}”</blockquote>
        <Button size="sm" className="mt-3" onClick={() => open(list, Math.max(0, list.indexOf(citation)))}>Open source</Button>
      </PopoverContent>
    </Popover>
  );
}

export function Chips({ citations }: { citations?: Citation[] | null }) {
  if (!citations?.length) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-0.5 align-baseline">
      {citations.map((c, i) => <CitationChip key={i} citation={c} siblings={citations} />)}
    </span>
  );
}
```

`frontend/components/citations/Cited.tsx`:
```tsx
import { NotFoundText } from "@/components/common/states";
import { isNotFound, type MaybeFound } from "@/lib/types";
import { Chips } from "./CitationChip";

/** Renders a cited value with chips, or "not found in file". Never a blank, never a guess. */
export function Cited<T>({ value, render }: { value: MaybeFound<T> | null | undefined; render?: (v: T) => React.ReactNode }) {
  if (value == null || isNotFound(value)) return <NotFoundText />;
  return <span>{render ? render(value.value) : String(value.value)}<Chips citations={value.citations} /></span>;
}
```

- [ ] **Step 3: Mount provider in attorney layout**

In `frontend/app/(attorney)/layout.tsx`, import `SourceDrawerProvider` from `@/components/citations/SourceDrawer` and wrap the outer `<div>` contents: `<SourceDrawerProvider>…header… {children}</SourceDrawerProvider>`.

- [ ] **Step 4: Verify against stubs**

Temporarily render on `app/(attorney)/matters/page.tsx`:
```tsx
"use client";
import { Chips } from "@/components/citations/CitationChip";
import { useApi } from "@/lib/use-api";
import type { Timeline } from "@/lib/types";
export default function Page() {
  const { data } = useApi<Timeline>("/api/matters/1001/timeline");
  return <div className="p-8">{data?.items.map((i) => <div key={i.record_id}>{i.title}<Chips citations={i.citations} /></div>)}</div>;
}
```
Signed in as attorney, click a chip → popover shows the excerpt → "Open source" → drawer shows the stub record with a yellow `<mark>` on the span. A document citation with `page` loads `/pages/{n}` text. Prev/next cycles. (Task 5 replaces this page.)

Run: `cd frontend && npm run lint && npm test` → clean.

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(product): citation chip, popover, Source Drawer with span highlight (F3)"
```

---

### Task 5: Matters list, matter shell, header + status pill, F1 "Since your last visit" (PLAN 2.4a)

**Files:**
- Create: `frontend/components/attorney/{MatterHeader.tsx,SinceLastVisit.tsx,CostPill.tsx}`
- Modify: `frontend/app/(attorney)/matters/page.tsx`, `frontend/app/(attorney)/matters/[id]/page.tsx`

**Interfaces:**
- Consumes: `useApi`, `api`, `Cited`, `Chips`, types `Overview`, `VisitResponse`, `Changes`, `Delta`, `DigestRun`, `AiCostReport`, `MatterSummary`
- Produces: `<MatterHeader overview/>`, `<SinceLastVisit matterId/>`, `<CostPill matterId/>`; matter page shell with `Tabs` ("brief" | "deep" | "cost") and a right column slot for `<AskPanel>` (Task 7)

- [ ] **Step 1: Matters list**

`frontend/app/(attorney)/matters/page.tsx`:
```tsx
"use client";
import Link from "next/link";
import { ErrorNote, Loading } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { API_URL } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import type { MatterSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type SyncStatus = { connected: boolean; clio_user?: string | null; last_synced_at?: string | null };

export default function MattersPage() {
  const matters = useApi<MatterSummary[]>("/api/matters");
  const sync = useApi<SyncStatus>("/api/sync/status");
  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">Matters</h1>
        <span className="text-xs text-muted-foreground">
          {sync.data?.connected ? `Clio connected${sync.data.clio_user ? ` as ${sync.data.clio_user}` : ""} · last sync ${fmtDate(sync.data.last_synced_at)}` : "Clio not connected"}
        </span>
        {!sync.data?.connected && <Button asChild size="sm" className="ml-auto"><a href={`${API_URL}/auth/clio/login`}>Connect Clio</a></Button>}
      </div>
      <ErrorNote error={matters.error} />
      {matters.loading ? <Loading /> : (
        <ul className="divide-y rounded border">
          {matters.data?.map((m) => (
            <li key={m.id}>
              <Link href={`/matters/${m.id}`} className="flex items-center gap-3 p-3 hover:bg-muted/50">
                <span className="font-medium">{m.client_name ?? m.description}</span>
                <span className="text-sm text-muted-foreground">{m.display_number} · {m.description}</span>
                {m.stage && <Badge variant="secondary" className="ml-auto">{m.stage}</Badge>}
                <span className="text-xs text-muted-foreground">{fmtDate(m.last_activity_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Cost pill (F9/F10)**

`frontend/components/attorney/CostPill.tsx`:
```tsx
"use client";
import { fmtDateTime, usd } from "@/lib/format";
import type { AiCostReport, DigestRun } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function CostPill({ matterId, lastSyncedAt }: { matterId: number; lastSyncedAt?: string | null }) {
  const runs = useApi<DigestRun[]>(`/api/matters/${matterId}/digest-runs`);
  const costs = useApi<AiCostReport>(`/api/ai-costs?matter_id=${matterId}`);
  const last = runs.data?.at(-1);
  return (
    <span className="inline-flex flex-wrap items-center gap-1 rounded-full border px-3 py-0.5 text-xs text-muted-foreground">
      {lastSyncedAt && <span>Synced {fmtDateTime(lastSyncedAt)}</span>}
      {last && <span>· Digested {fmtDateTime(last.finished_at ?? last.started_at)}</span>}
      {last?.cache_hit && <span className="font-medium text-emerald-700 dark:text-emerald-400">· cache hit</span>}
      {last && <span>· {usd(last.cost_usd)}</span>}
      {costs.data && <span>(case {usd(costs.data.total_usd)})</span>}
    </span>
  );
}
```

Digest-runs order is unknown. If Dev 1 returns newest-first, swap `.at(-1)` for `[0]`; check the stub fixture order and confirm with Dev 1 at the checkpoint.

- [ ] **Step 3: Header**

`frontend/components/attorney/MatterHeader.tsx`:
```tsx
"use client";
import { AlertTriangle, User } from "lucide-react";
import { Cited } from "@/components/citations/Cited";
import { Chips } from "@/components/citations/CitationChip";
import { apiUrl } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { isNotFound, type Overview } from "@/lib/types";
import { CostPill } from "./CostPill";

export function MatterHeader({ overview: o }: { overview: Overview }) {
  const lcc = isNotFound(o.last_client_contact) ? null : o.last_client_contact;
  return (
    <section className="space-y-2">
      <CostPill matterId={o.matter.id} lastSyncedAt={o.last_synced_at} />
      <div className="flex items-start gap-4">
        {o.client.photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={apiUrl(o.client.photo_url)} alt="Client" className="h-16 w-16 rounded object-cover" />
        ) : <div className="grid h-16 w-16 place-items-center rounded bg-muted"><User className="h-8 w-8 text-muted-foreground" /></div>}
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">
            {o.client.name}{o.client.age != null && <span className="font-normal text-muted-foreground"> · {o.client.age}y</span>}
            {o.client.photo_citation && <Chips citations={[o.client.photo_citation]} />}
          </h1>
          <p className="text-sm">
            DOI <Cited value={o.date_of_incident} render={(v: string) => fmtDate(v)} /> · SOL <Cited value={o.statute_of_limitations} render={(v: string) => fmtDate(v)} />
          </p>
          <p className="text-sm">
            Last client contact:{" "}
            {lcc ? (
              <span className={lcc.value.days_ago > 30 ? "font-medium text-amber-700 dark:text-amber-400" : ""}>
                {lcc.value.days_ago}d ago · {lcc.value.channel}{lcc.value.by && ` · ${lcc.value.by}`}
                <Chips citations={lcc.citations} />
                {lcc.value.days_ago > 30 && <AlertTriangle className="ml-1 inline h-4 w-4" />}
              </span>
            ) : <Cited value={o.last_client_contact} />}
          </p>
        </div>
        <StageBar stages={o.stage.stages} index={o.stage.index ?? null} current={o.stage.current ?? null} />
      </div>
    </section>
  );
}

function StageBar({ stages, index, current }: { stages: string[]; index: number | null; current: string | null }) {
  if (!stages.length) return current ? <span className="ml-auto text-sm">Stage: {current}</span> : null;
  return (
    <ol className="ml-auto flex gap-1 text-[11px]">
      {stages.map((s, i) => (
        <li key={s} className={`rounded px-2 py-1 ${index != null && i <= index ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{s}</li>
      ))}
    </ol>
  );
}
```

- [ ] **Step 4: F1 panel**

`frontend/components/attorney/SinceLastVisit.tsx`:
```tsx
"use client";
import { useEffect, useState } from "react";
import { Chips } from "@/components/citations/CitationChip";
import { ErrorNote, Loading } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { fmtDate, fmtDateTime } from "@/lib/format";
import type { Changes, Delta, VisitResponse } from "@/lib/types";

/** F1. POST /visits → baseline → /changes + /delta. Badges are computed per request, never cached client-side. */
export function SinceLastVisit({ matterId }: { matterId: number }) {
  const [s, set] = useState<{ visit?: VisitResponse; changes?: Changes; delta?: Delta; error?: Error }>({});
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // React dev StrictMode runs this twice; the backend reuses visits within 30 min, so the baseline is stable.
        const visit = await api<VisitResponse>(`/api/matters/${matterId}/visits`, { method: "POST" });
        const q = visit.previous_visit_at ? `?since=${encodeURIComponent(visit.previous_visit_at)}` : "";
        const [changes, delta] = await Promise.all([
          api<Changes>(`/api/matters/${matterId}/changes${q}`),
          api<Delta>(`/api/matters/${matterId}/delta${q}`).catch(() => undefined),
        ]);
        if (!cancelled) set({ visit, changes, delta });
      } catch (error) {
        if (!cancelled) set({ error: error as Error });
      }
    })();
    return () => { cancelled = true; };
  }, [matterId]);

  const { visit, changes, delta } = s;
  const title = changes?.first_visit || visit?.first_visit
    ? "🆕 First time opening this matter, showing the last 14 days"
    : `🆕 Since your last visit (${fmtDateTime(changes?.since ?? visit?.previous_visit_at)})${changes ? ` · ${changes.items.length} changes, by importance` : ""}`;

  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">{title}</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm">
        <ErrorNote error={s.error} />
        {!changes && !s.error && <Loading />}
        {delta && delta.summary.length > 0 && (
          <p className="rounded bg-muted/50 p-2">{delta.summary.map((sen, i) => <span key={i}>{sen.text}<Chips citations={sen.citations} /> </span>)}</p>
        )}
        {changes && changes.items.length === 0 && (
          <p className="text-muted-foreground">
            {changes.empty_message ?? `Nothing has changed since your last visit (${fmtDateTime(changes.since)}).`}
            {changes.last_activity && <> Last activity on the case: {fmtDate(changes.last_activity.at)}, {changes.last_activity.description}<Chips citations={changes.last_activity.citations} /></>}
          </p>
        )}
        <ul className="space-y-1">
          {changes?.items.map((c) => (
            <li key={`${c.record_id}-${c.change}`} className="flex gap-2">
              <span className="w-5 text-right font-mono font-semibold">{c.importance ?? "–"}</span>
              <div>
                <span className="font-medium">{c.title}</span>
                {c.change !== "changed" && <Badge variant="outline" className="ml-1 text-[10px]">{c.change}</Badge>}
                <Chips citations={c.citations} />
                {c.why_it_matters && <span className="text-muted-foreground"> · why: {c.why_it_matters}</span>}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 5: Matter page shell**

`frontend/app/(attorney)/matters/[id]/page.tsx`:
```tsx
"use client";
import Link from "next/link";
import { use } from "react";
import { MatterHeader } from "@/components/attorney/MatterHeader";
import { SinceLastVisit } from "@/components/attorney/SinceLastVisit";
import { ErrorNote, Loading } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Overview } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function MatterPage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  const overview = useApi<Overview>(`/api/matters/${matterId}/overview`);
  return (
    <div className="grid h-[calc(100vh-45px)] grid-cols-[1fr_400px]">
      <main className="space-y-4 overflow-y-auto p-4">
        <ErrorNote error={overview.error} />
        {overview.data ? <MatterHeader overview={overview.data} /> : <Loading />}
        <Tabs defaultValue="brief">
          <div className="flex items-center">
            <TabsList>
              <TabsTrigger value="brief">Brief</TabsTrigger>
              <TabsTrigger value="deep">Deep-Dive</TabsTrigger>
              <TabsTrigger value="cost">AI cost</TabsTrigger>
            </TabsList>
            <Button asChild size="sm" className="ml-auto"><Link href={`/matters/${matterId}/share`}>Share ▸</Link></Button>
          </div>
          <TabsContent value="brief" className="space-y-4">
            <SinceLastVisit matterId={matterId} />
            {/* Task 6: BriefGrid */}
          </TabsContent>
          <TabsContent value="deep">{/* Task 6: full ranked timeline (Deep-Dive stretch) */}</TabsContent>
          <TabsContent value="cost">{/* Task 13: AiCostTab */}</TabsContent>
        </Tabs>
      </main>
      <aside className="border-l">{/* Task 7: AskPanel */}</aside>
    </div>
  );
}
```

- [ ] **Step 6: Verify against stubs**

Open `/matters` → stub matter listed → click → header (photo placeholder or stub photo, DOI/SOL chips, ⚠ when > 30 days), cost pill, F1 panel with ranked changes and chips. Chips open the drawer. Run `npm run lint`.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "feat(product): matters list, matter header + cost pill, F1 since-last-visit panel"
```

---

### Task 6: Brief widgets: worth, coverage, spend, deadlines, story, key moments, injuries, providers (PLAN 2.4b, F2/F4)

**Files:**
- Create: `frontend/components/attorney/{BriefGrid.tsx,WorthTile.tsx,CoverageTile.tsx,SpendTile.tsx,DeadlinesBoard.tsx,StorySoFar.tsx,KeyMoments.tsx,InjuriesPanel.tsx,ProvidersPanel.tsx}`
- Modify: `frontend/app/(attorney)/matters/[id]/page.tsx` (render `<BriefGrid>` in the brief tab and `<KeyMoments showAll>` in deep)

**Interfaces:**
- Consumes: `Cited`, `Chips`, `useApi`, `fmtMoney`, `fmtMoneyShort`, `fmtDate`, types `Brief`, `Overview`, `Costs`, `Deadlines`, `Providers`, `Grant`, `Timeline`
- Produces: `<BriefGrid matterId overview?/>`

- [ ] **Step 1: Tiles**

`frontend/components/attorney/WorthTile.tsx`:
```tsx
import { Chips } from "@/components/citations/CitationChip";
import { NotFoundText } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtMoneyShort } from "@/lib/format";
import { isNotFound, type Brief } from "@/lib/types";

export function WorthTile({ worth }: { worth: Brief["worth"] }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">Case worth <Badge variant="outline">Estimate</Badge></CardTitle></CardHeader>
      <CardContent className="space-y-1 text-sm">
        {isNotFound(worth) ? <NotFoundText /> : (
          <>
            <p className="text-2xl font-semibold">{fmtMoneyShort(worth.low)} – {fmtMoneyShort(worth.high)}</p>
            <ul className="space-y-0.5">
              {worth.assumptions.map((a) => (
                <li key={a.label}>• {a.label}: {a.not_found ? <NotFoundText /> : a.text}<Chips citations={a.citations} /></li>
              ))}
            </ul>
            {worth.cap_note && <p className="text-amber-700 dark:text-amber-400">{worth.cap_note}</p>}
            <details className="text-xs text-muted-foreground"><summary>Why this range?</summary>{worth.method}</details>
          </>
        )}
      </CardContent>
    </Card>
  );
}
```

`frontend/components/attorney/CoverageTile.tsx`:
```tsx
import { Cited } from "@/components/citations/Cited";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Brief } from "@/lib/types";

const ROWS = [["carrier", "Carrier"], ["bi_per_person", "BI per person"], ["bi_per_accident", "BI per accident"], ["um_uim", "UM/UIM"], ["medpay", "MedPay"]] as const;

export function CoverageTile({ coverage }: { coverage: Brief["coverage"] }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">Coverage</CardTitle></CardHeader>
      <CardContent>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          {ROWS.map(([k, label]) => (
            <div key={k} className="contents"><dt className="text-muted-foreground">{label}</dt><dd><Cited value={coverage[k]} /></dd></div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
```

`frontend/components/attorney/SpendTile.tsx`:
```tsx
"use client";
import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";
import { Chips } from "@/components/citations/CitationChip";
import { Cited } from "@/components/citations/Cited";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtMoney } from "@/lib/format";
import type { Costs } from "@/lib/types";

export function SpendTile({ costs }: { costs?: Costs }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">Firm spend</CardTitle></CardHeader>
      <CardContent className="space-y-1 text-sm">
        {costs && <p className="text-lg font-semibold"><Cited value={costs.total} render={(v: number) => fmtMoney(v)} /></p>}
        {costs && costs.monthly.length > 1 && (
          <div className="h-12"><ResponsiveContainer><AreaChart data={costs.monthly}>
            <Tooltip formatter={(v: number) => fmtMoney(v)} labelFormatter={(_, p) => p?.[0]?.payload?.month ?? ""} />
            <Area dataKey="amount" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.15} />
          </AreaChart></ResponsiveContainer></div>
        )}
        <ul className="text-xs">{costs?.by_category.map((c) => <li key={c.category}>{c.category}: {fmtMoney(c.amount)}<Chips citations={c.citations} /></li>)}</ul>
      </CardContent>
    </Card>
  );
}
```

`frontend/components/attorney/DeadlinesBoard.tsx`:
```tsx
import { Chips } from "@/components/citations/CitationChip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtDate } from "@/lib/format";
import type { DeadlineItem, Deadlines } from "@/lib/types";

export function DeadlinesBoard({ deadlines }: { deadlines?: Deadlines }) {
  const cols: [string, DeadlineItem[]][] = [["⏰ Overdue", deadlines?.overdue ?? []], ["Coming", deadlines?.upcoming ?? []], ["Waiting on", deadlines?.waiting_on ?? []]];
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">Overdue · Coming · Waiting on</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-3 gap-2 text-xs">
        {cols.map(([title, items]) => (
          <div key={title}>
            <p className="mb-1 font-medium">{title} ({items.length})</p>
            <ul className="space-y-1">
              {items.map((d) => (
                <li key={d.id} className={d.overdue ? "text-destructive" : ""}>
                  {d.due_at && <span className="font-mono">{fmtDate(d.due_at)} </span>}{d.title}
                  {d.waiting_on && <span className="text-muted-foreground"> · {d.waiting_on}</span>}
                  <Chips citations={d.citations} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```

`frontend/components/attorney/StorySoFar.tsx`:
```tsx
import { Chips } from "@/components/citations/CitationChip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Brief } from "@/lib/types";

export function StorySoFar({ story }: { story: Brief["story"] }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">📝 Story so far</CardTitle></CardHeader>
      <CardContent><ul className="list-disc space-y-1 pl-4 text-sm">{story.map((s, i) => <li key={i}>{s.text}<Chips citations={s.citations} /></li>)}</ul></CardContent>
    </Card>
  );
}
```

`frontend/components/attorney/KeyMoments.tsx`:
```tsx
"use client";
import { useState } from "react";
import { Chips } from "@/components/citations/CitationChip";
import { Loading } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtDate } from "@/lib/format";
import type { Brief, Timeline } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function KeyMoments({ matterId, brief, showAll: initial = false }: { matterId: number; brief?: Brief; showAll?: boolean }) {
  const [showAll, setShowAll] = useState(initial);
  const timeline = useApi<Timeline>(showAll ? `/api/matters/${matterId}/timeline` : null);
  const ranked = timeline.data ? [...timeline.data.items].sort((a, b) => (b.importance ?? 0) - (a.importance ?? 0)) : [];
  return (
    <Card>
      <CardHeader className="flex-row items-center pb-1">
        <CardTitle className="text-sm">⭐ Key moments{brief && ` · ${brief.key_moments.length} of ${brief.total_records}`}</CardTitle>
        <Button variant="link" size="sm" className="ml-auto" onClick={() => setShowAll((v) => !v)}>{showAll ? "Top moments only" : "Show all ▸"}</Button>
      </CardHeader>
      <CardContent className="text-sm">
        {!showAll && (
          <ol className="space-y-1">
            {brief?.key_moments.map((k) => (
              <li key={k.rank} className="flex gap-2">
                <span className="w-6 text-right font-mono font-semibold">{k.importance}</span>
                <span className="w-24 shrink-0 font-mono text-xs">{fmtDate(k.date)}</span>
                <span><span className="font-medium">{k.title}</span> <span className="text-muted-foreground">· {k.rank_reason}</span><Chips citations={k.citations} /></span>
              </li>
            ))}
          </ol>
        )}
        {showAll && (timeline.loading ? <Loading /> : (
          <ol className="max-h-[60vh] space-y-1 overflow-y-auto">
            {ranked.map((t) => (
              <li key={t.record_id} className="flex gap-2">
                <span className="w-6 text-right font-mono">{t.importance ?? "–"}</span>
                <span className="w-24 shrink-0 font-mono text-xs">{fmtDate(t.occurred_at)}</span>
                <span>{t.one_liner ?? t.title}<Chips citations={t.citations} /></span>
              </li>
            ))}
          </ol>
        ))}
      </CardContent>
    </Card>
  );
}
```

`frontend/components/attorney/InjuriesPanel.tsx`:
```tsx
import { Chips } from "@/components/citations/CitationChip";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Brief } from "@/lib/types";

/** Generic body regions → SVG rects on a simple figure (no case data). */
const REGIONS: Record<string, [number, number, number, number]> = {
  head: [40, 0, 20, 20], neck: [44, 20, 12, 8], shoulder: [25, 28, 50, 8], chest: [32, 36, 36, 20],
  back: [32, 36, 36, 34], lumbar: [34, 58, 32, 12], arm: [16, 36, 12, 40], hand: [12, 76, 12, 10],
  hip: [32, 70, 36, 10], leg: [34, 80, 32, 50], knee: [34, 102, 32, 8], foot: [34, 130, 32, 8],
};
const regionOf = (r?: string | null) => Object.keys(REGIONS).find((k) => (r ?? "").toLowerCase().includes(k)) ?? null;

export function InjuriesPanel({ injuries }: { injuries: Brief["injuries"] }) {
  const hit = new Set(injuries.map((i) => regionOf(i.body_region ?? i.name)).filter(Boolean));
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">🩺 Injuries</CardTitle></CardHeader>
      <CardContent className="flex gap-4 text-sm">
        <svg viewBox="0 0 100 140" className="h-40 w-24 shrink-0" aria-label="Body map">
          {Object.entries(REGIONS).map(([k, [x, y, w, h]]) => (
            <rect key={k} x={x} y={y} width={w} height={h} rx={3} className={hit.has(k) ? "fill-destructive/70" : "fill-muted"} />
          ))}
        </svg>
        <ul className="space-y-1">
          {injuries.map((i) => (
            <li key={i.name}>
              <span className={i.primary ? "font-semibold" : ""}>{i.name}</span>
              {i.severity_tier && <Badge variant="outline" className="ml-1 text-[10px]">{i.severity_tier.replace("_", " ")}</Badge>}
              <Chips citations={i.citations} />
              {i.description && <p className="text-xs text-muted-foreground">{i.description}</p>}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
```

`frontend/components/attorney/ProvidersPanel.tsx`:
```tsx
import Link from "next/link";
import { Cited } from "@/components/citations/Cited";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtDate, fmtMoneyShort } from "@/lib/format";
import type { Grant, Providers } from "@/lib/types";

export function ProvidersPanel({ matterId, providers, grants }: { matterId: number; providers?: Providers; grants?: Grant[] }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">👩‍⚕️ Providers · liens · shares</CardTitle></CardHeader>
      <CardContent>
        <ul className="space-y-2 text-sm">
          {providers?.providers.map((p) => {
            const g = grants?.find((x) => x.provider_contact_id === p.contact_id && !x.revoked_at);
            return (
              <li key={p.contact_id}>
                <span className="font-medium">{p.name}</span>{" "}
                <Cited value={p.billed} render={(v: number) => fmtMoneyShort(v)} />
                {p.lien && <Badge variant="outline" className="ml-1 text-[10px]">LIEN</Badge>}
                <span className="text-xs text-muted-foreground">
                  {" "}· balance <Cited value={p.balance} render={(v: number) => fmtMoneyShort(v)} />
                  {p.last_visit && ` · last visit ${fmtDate(p.last_visit)}`}
                  {p.current_gap_days != null && p.current_gap_days > 30 && ` · ${p.current_gap_days}d gap`}
                </span>
                <div className="text-xs">
                  {g?.latest_version
                    ? <Link className="underline" href={`/matters/${matterId}/share?provider=${p.contact_id}`}>v{g.latest_version} shared {fmtDate(g.released_at)} · opened {g.view_count}× [audit ▸]</Link>
                    : <Link className="underline" href={`/matters/${matterId}/share?provider=${p.contact_id}`}>Not shared · Share ▸</Link>}
                </div>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2: Grid + wire into page**

`frontend/components/attorney/BriefGrid.tsx`:
```tsx
"use client";
import { ErrorNote, Loading } from "@/components/common/states";
import type { Brief, Costs, Deadlines, Grant, Providers } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { CoverageTile } from "./CoverageTile";
import { DeadlinesBoard } from "./DeadlinesBoard";
import { InjuriesPanel } from "./InjuriesPanel";
import { KeyMoments } from "./KeyMoments";
import { ProvidersPanel } from "./ProvidersPanel";
import { SpendTile } from "./SpendTile";
import { StorySoFar } from "./StorySoFar";
import { WorthTile } from "./WorthTile";

export function BriefGrid({ matterId }: { matterId: number }) {
  const brief = useApi<Brief>(`/api/matters/${matterId}/brief`);
  const costs = useApi<Costs>(`/api/matters/${matterId}/costs`);
  const deadlines = useApi<Deadlines>(`/api/matters/${matterId}/deadlines`);
  const providers = useApi<Providers>(`/api/matters/${matterId}/providers`);
  const grants = useApi<Grant[]>(`/api/matters/${matterId}/shares`);
  if (brief.error) return <ErrorNote error={brief.error} />;
  if (!brief.data) return <Loading lines={10} />;
  const b = brief.data;
  return (
    <div className="space-y-4">
      {b.stale && <p className="text-xs text-amber-700">Records changed since the last digest; some facts may be out of date.</p>}
      <div className="grid grid-cols-2 gap-4"><WorthTile worth={b.worth} /><CoverageTile coverage={b.coverage} /></div>
      <div className="grid grid-cols-[1fr_1.4fr_1.4fr] gap-4">
        <SpendTile costs={costs.data} /><DeadlinesBoard deadlines={deadlines.data} /><StorySoFar story={b.story} />
      </div>
      <KeyMoments matterId={matterId} brief={b} />
      <div className="grid grid-cols-2 gap-4">
        <InjuriesPanel injuries={b.injuries} />
        <ProvidersPanel matterId={matterId} providers={providers.data} grants={grants.data} />
      </div>
    </div>
  );
}
```

In `matters/[id]/page.tsx`, replace `{/* Task 6: BriefGrid */}` with `<BriefGrid matterId={matterId} />` and the Deep-Dive placeholder with `<KeyMoments matterId={matterId} showAll />` (imports from `@/components/attorney/...`).

- [ ] **Step 3: Verify against stubs**

Every tile renders from fixtures. Click one chip in each tile (worth assumption, coverage carrier, a deadline, a story bullet, a key moment, an injury, provider billed) → drawer opens. Coverage rows that are NotFound show "not found in file". Run `npm run lint && npm run build`.

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(product): brief widgets — worth, coverage, spend, deadlines, story, key moments, injuries, providers (F2/F4)"
```

---

### Task 7: Ask panel: SSE answers, highlight-to-source, Verify selection (PLAN 2.5)

**Files:**
- Create: `frontend/lib/selection.ts`, `frontend/lib/selection.test.ts`, `frontend/components/attorney/AskPanel.tsx`
- Modify: `frontend/app/(attorney)/matters/[id]/page.tsx` (mount in `<aside>`)

**Interfaces:**
- Consumes: `postSSE`, `api`, `uniqueCitations`, `CitationChip`, `useSourceDrawer`, types `AnswerSegment`, `LocateResult`, `SuggestedQuestions`
- Produces: `selectionSources(segments, ids) -> {citations, needsVerify}`, `segmentIdsInRange(root, range) -> string[]`, `<AskPanel matterId/>`

- [ ] **Step 1: Failing test**

`frontend/lib/selection.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { selectionSources } from "./selection";

const cite = (id: string) => ({ record_id: id, source_type: "note" as const, title: id, char_start: 0, char_end: 1, excerpt: "x" });
const segs = [
  { id: "s1", text: "MRI confirms a herniation", citations: [cite("document:1")] },
  { id: "s2", text: " and ", citations: [] },
  { id: "s3", text: "PT for strain", citations: [cite("note:2"), cite("document:1")] },
];

describe("selectionSources", () => {
  it("unions citations of the selected segments", () => {
    const r = selectionSources(segs, ["s1", "s3"]);
    expect(r.citations.map((c) => c.record_id)).toEqual(["document:1", "note:2"]);
    expect(r.needsVerify).toBe(false);
  });
  it("asks to verify when an uncited segment is selected", () => {
    expect(selectionSources(segs, ["s2"]).needsVerify).toBe(true);
    expect(selectionSources(segs, ["s2"]).citations).toEqual([]);
  });
  it("ignores unknown ids", () => {
    expect(selectionSources(segs, ["zz"])).toEqual({ citations: [], needsVerify: false });
  });
});
```

- [ ] **Step 2: Run, expect failure**

Run: `cd frontend && npm test -- selection` → FAIL (module missing).

- [ ] **Step 3: Implement**

`frontend/lib/selection.ts`:
```ts
import { uniqueCitations } from "./citations";
import type { AnswerSegment } from "./types";

export function selectionSources(segments: AnswerSegment[], ids: string[]) {
  const chosen = segments.filter((s) => ids.includes(s.id));
  return {
    citations: uniqueCitations(chosen.flatMap((s) => s.citations ?? [])),
    needsVerify: chosen.some((s) => !s.citations?.length),
  };
}

/** DOM side: which [data-seg] spans inside root does the range touch? */
export function segmentIdsInRange(root: HTMLElement, range: Range): string[] {
  return [...root.querySelectorAll<HTMLElement>("[data-seg]")]
    .filter((el) => range.intersectsNode(el))
    .map((el) => el.dataset.seg!)
    .filter(Boolean);
}
```

Run: `npm test` → PASS.

- [ ] **Step 4: Ask panel**

`frontend/components/attorney/AskPanel.tsx`:
```tsx
"use client";
import { Send } from "lucide-react";
import { useRef, useState } from "react";
import { CitationChip } from "@/components/citations/CitationChip";
import { useSourceDrawer } from "@/components/citations/SourceDrawer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { chipLabel } from "@/lib/citations";
import { segmentIdsInRange, selectionSources } from "@/lib/selection";
import { postSSE } from "@/lib/sse";
import type { AnswerSegment, Citation, LocateResult, SuggestedQuestions } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type Turn = { question: string; segments: AnswerSegment[]; followups: string[]; status?: string; error?: string; done: boolean };
type Pop = { x: number; y: number; text: string; citations: Citation[]; needsVerify: boolean; verify?: LocateResult | "loading" };

export function AskPanel({ matterId }: { matterId: number }) {
  const suggested = useApi<SuggestedQuestions>(`/api/matters/${matterId}/suggested-questions`);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [pop, setPop] = useState<Pop | null>(null);
  const answersRef = useRef<HTMLDivElement>(null);
  const { open } = useSourceDrawer();
  const busy = turns.some((t) => !t.done);

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    setQ("");
    const history = turns.filter((t) => t.done && !t.error).map((t) => ({ question: t.question, answer_text: t.segments.map((s) => s.text).join("") }));
    const idx = turns.length;
    const patch = (fn: (t: Turn) => Turn) => setTurns((ts) => ts.map((t, i) => (i === idx ? fn(t) : t)));
    setTurns((ts) => [...ts, { question, segments: [], followups: [], done: false }]);
    try {
      await postSSE(`/api/matters/${matterId}/ask`, { question, history }, ({ event, data }) => {
        const d = data as Record<string, unknown>;
        if (event === "segment") patch((t) => ({ ...t, status: undefined, segments: [...t.segments, d as unknown as AnswerSegment] }));
        else if (event === "status") patch((t) => ({ ...t, status: String(d.message ?? "") }));
        else if (event === "done") patch((t) => ({ ...t, done: true, status: undefined, followups: (d.followups as string[]) ?? [] }));
        else if (event === "error") patch((t) => ({ ...t, done: true, error: String(d.message ?? "Something went wrong") }));
      });
      patch((t) => (t.done ? t : { ...t, done: true }));
    } catch (e) {
      patch((t) => ({ ...t, done: true, error: String(e) }));
    }
  }

  function onMouseUp() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !answersRef.current) { setPop(null); return; }
    const range = sel.getRangeAt(0);
    const ids = segmentIdsInRange(answersRef.current, range);
    if (!ids.length) { setPop(null); return; }
    const all = turns.flatMap((t) => t.segments);
    const { citations, needsVerify } = selectionSources(all, ids);
    const rect = range.getBoundingClientRect();
    setPop({ x: rect.left, y: rect.bottom + 6, text: sel.toString().trim(), citations, needsVerify });
  }

  async function verify() {
    if (!pop) return;
    setPop({ ...pop, verify: "loading" });
    try {
      const r = await api<LocateResult>(`/api/matters/${matterId}/locate`, { json: { text: pop.text } });
      setPop((p) => p && { ...p, verify: r });
    } catch {
      setPop((p) => p && { ...p, verify: { supported: false, citations: [], explanation: "Verification failed." } });
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-3">
        <p className="text-sm font-semibold">💬 Ask the case</p>
        <div className="mt-2 flex flex-wrap gap-1">
          {suggested.data?.questions.map((s) => <Button key={s} variant="outline" size="sm" className="h-auto py-1 text-xs" onClick={() => ask(s)}>{s}</Button>)}
        </div>
      </div>
      <div ref={answersRef} onMouseUp={onMouseUp} className="flex-1 space-y-4 overflow-y-auto p-3 text-sm">
        {turns.map((t, i) => (
          <div key={i} className="space-y-1">
            <p className="font-medium">Q: {t.question}</p>
            <p className="leading-relaxed">
              {t.segments.map((s) => (
                <span key={s.id} data-seg={s.id}>
                  {s.text}
                  {s.citations?.map((c, j) => <sup key={j}><CitationChip citation={c} siblings={s.citations} /></sup>)}
                </span>
              ))}
              {!t.done && <span className="animate-pulse text-muted-foreground"> {t.status ?? "…"}</span>}
            </p>
            {t.error && <p className="text-destructive">⚠ {t.error}</p>}
            {t.followups.length > 0 && (
              <div className="flex flex-wrap gap-1">{t.followups.map((f) => <Button key={f} variant="ghost" size="sm" className="h-auto py-0.5 text-xs" onClick={() => ask(f)}>↳ {f}</Button>)}</div>
            )}
          </div>
        ))}
      </div>
      {pop && (
        <div className="fixed z-50 w-80 rounded-md border bg-popover p-3 text-sm shadow-md" style={{ left: Math.min(pop.x, window.innerWidth - 340), top: pop.y }}>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Sources for selection</p>
          <ul className="space-y-1">
            {pop.citations.map((c, i) => (
              <li key={i}><button className="text-left hover:underline" onClick={() => open(pop.citations, i)}>[{chipLabel(c)}] {c.title}{c.page != null && ` p.${c.page}`} ▸</button></li>
            ))}
          </ul>
          {pop.needsVerify && !pop.verify && <Button size="sm" variant="outline" className="mt-2" onClick={verify}>Verify selection</Button>}
          {pop.verify === "loading" && <p className="mt-2 text-muted-foreground">Checking the case file…</p>}
          {pop.verify && pop.verify !== "loading" && (pop.verify.supported && pop.verify.citations.length ? (
            <ul className="mt-2 space-y-1 border-t pt-2">
              {pop.verify.citations.map((c, i) => (
                <li key={i}><button className="text-left hover:underline" onClick={() => open((pop.verify as LocateResult).citations, i)}>✔ [{chipLabel(c)}] {c.excerpt.slice(0, 80)}… ▸</button></li>
              ))}
            </ul>
          ) : <p className="mt-2 text-muted-foreground">No supporting source found in the case file.</p>)}
        </div>
      )}
      <form className="flex gap-2 border-t p-3" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask anything about this case…" disabled={busy} />
        <Button type="submit" size="icon" disabled={busy || !q.trim()}><Send className="h-4 w-4" /></Button>
      </form>
    </div>
  );
}
```

Mount: in `matters/[id]/page.tsx` replace `{/* Task 7: AskPanel */}` with `<AskPanel matterId={matterId} />`.

- [ ] **Step 5: Verify against the stub SSE**

Click a suggested question → stub segments stream in one by one with superscript chips. Highlight text spanning two segments → popover lists the union of sources → clicking one opens the drawer. Highlight an uncited connective segment → "Verify selection" → stub `/locate` result listed. Clicking outside clears the popover. `npm run lint && npm test`.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(product): Ask panel — SSE answers, highlight-to-source, verify selection"
```

---

### Task 8: Sharing core: Dev 1 adapter + ProviderProjection + request view (PLAN 2.6a, F6)

**Files:**
- Modify: `backend/app/sharing/sources.py` (full adapter)
- Create: `backend/app/sharing/requests.py`, `backend/app/sharing/projection.py`
- Test: `backend/tests/test_sharing.py` (append)

**Interfaces:**
- Consumes: interface doc (Task 0); `jload`, `now_iso`; contracts `Coverage`, `WorthEstimate`, `NotFound`, `ProviderCase`, `SharePolicy`, section models
- Produces:
  - `sources.data_dir()`, `matter(db, id)`, `patient_display(db, id) -> str`, `stage(db, id) -> StageShare | None`, `last_activity_at(db, id, until) -> str | None`, `movements(db, id, until, limit=5) -> list[Movement]`, `provider_identity(db, contact_id) -> ProviderIdentity | None`, `provider_bills(db, matter_id, contact_id) -> ProviderBills | None`, `documents(db, matter_id) -> list[SharedDocument]`, `document_path(db, matter_id, document_id) -> Path | None`, `provider_request_rows(db, matter_id, contact_id)`, `provider_request(db, request_id)`, `coverage(db, id) -> Coverage | None`, `worth(db, id) -> WorthEstimate | None`, `treatment_visits(db, id) -> list[dict]`
  - `requests.requests_for(db, matter_id, contact_id, *, audience: "attorney"|"provider") -> list[ProviderRequest]`, `requests.set_state(db, request_id, state, user_id) -> None`
  - `projection.ALL_FIELDS`, `heartbeat_state(status, last_activity_at, today) -> HeartbeatState`, `Sections`, `build_sections(db, matter_id, provider_contact_id) -> Sections`, `project(sections, *, grant_id, policy, shared_by) -> ProviderCase`, `preview_policy(grant_id, documents) -> SharePolicy`

- [ ] **Step 1: Failing tests (append to `test_sharing.py`)**

```python
# ------------------------------------------------------------------------------------------- projection (2.6a, F6)
from datetime import date  # noqa: E402

from backend.app.contracts import SharePolicy  # noqa: E402
from backend.app.sharing import projection, sources  # noqa: E402


def _policy(fields, docs=(), detail="confirmed", note=None):
    return SharePolicy(grant_id=1, version=1, fields=list(fields), document_ids=list(docs), coverage_detail=detail,
                       status_note=note, released_at="2026-10-01T00:00:00Z")


def _case(db_path, fields, contact=PROV_A, **kw):
    with connect(db_path) as db:
        s = projection.build_sections(db, MATTER, contact)
    return projection.project(s, grant_id=1, policy=_policy(fields, **kw), shared_by="Firm Attorney").model_dump(
        mode="json", exclude_none=True)


def test_heartbeat_state_boundaries():
    today = date(2026, 10, 2)
    assert projection.heartbeat_state("open", "2026-09-02", today) == "active"     # 30d
    assert projection.heartbeat_state("open", "2026-09-01", today) == "quiet"      # 31d
    assert projection.heartbeat_state("open", "2026-07-04", today) == "quiet"      # 90d
    assert projection.heartbeat_state("open", "2026-07-03", today) == "dormant"    # 91d
    assert projection.heartbeat_state("Closed", "2026-10-01", today) == "closed"
    assert projection.heartbeat_state("open", None, today) == "dormant"


def test_only_granted_sections_exist(seeded):
    case = _case(seeded, ["status"])
    assert set(case) == {"grant_id", "policy_version", "patient_display", "firm_name", "shared_by", "updated_at",
                         "heartbeat"}
    assert case["patient_display"] == "P. E."


def test_every_field_maps_to_its_section(seeded):
    case = _case(seeded, projection.ALL_FIELDS, docs=["document:10"], detail="limits", note="Hello")
    for key in ("heartbeat", "coverage", "case_value", "bills", "requests", "documents", "adherence", "other_care",
                "status_note"):
        assert key in case, key


def test_last_movement_masks_confidential_activity(seeded):
    hb = _case(seeded, ["status"])["heartbeat"]
    assert hb["state"] == "active"
    assert hb["last_movement"] == {"date": days_ago(3), "text": "Case activity recorded"}
    assert [m["text"] for m in hb["recent_movement"]] == ["ER records received"]
    assert hb["stage"]["current"] == "Demand" and hb["stage"]["index"] == 2


def test_coverage_detail_variants(seeded):
    assert _case(seeded, ["coverage"])["coverage"] == {"confirmed": True}
    limits = _case(seeded, ["coverage"], detail="limits")["coverage"]
    assert limits["carrier"] == "Acme Mutual" and "BI per person $100,000" in limits["limits_text"]
    assert "UM/UIM" not in limits["limits_text"]          # not found → never invented


def test_sections_are_scoped_to_the_provider(seeded):
    a = _case(seeded, ["bills", "open_requests", "adherence", "other_care"])
    assert a["bills"]["billed"] == 1200.0 and a["bills"]["lien"] is True
    assert {r["id"] for r in a["requests"]} == {"req:1", "req:2"}
    assert len(a["adherence"]["visits"]) == 2 and a["adherence"]["gaps"][0]["days"] == 60
    assert [o["provider_name"] for o in a["other_care"]] == ["Provider B Clinic"]
    b = _case(seeded, ["bills", "open_requests"], contact=PROV_B)
    assert b["bills"]["billed"] == 500.0 and "balance" not in b["bills"]
    assert {r["id"] for r in b["requests"]} == {"req:3"}


def test_provider_sees_excerpt_only_when_addressed_to_them(seeded):
    reqs = {r["id"]: r for r in _case(seeded, ["open_requests"])["requests"]}
    assert reqs["req:1"]["citations"] == []
    assert reqs["req:2"]["citations"][0]["excerpt"] == "Please send an itemized bill"
    with connect(seeded) as db:
        full = projection.requests.requests_for(db, MATTER, PROV_A, audience="attorney")
    assert all(r.citations for r in full)


def test_documents_limited_to_policy(seeded):
    assert [d["id"] for d in _case(seeded, ["documents"], docs=["document:10"])["documents"]] == ["document:10"]
    assert _case(seeded, ["documents"])["documents"] == []


def test_empty_dev1_data_still_projects(db_path):
    from backend.tests.dev2_support import seed
    with connect(db_path) as db:
        seed(db, with_case_data=False)
    case = _case(db_path, projection.ALL_FIELDS)
    assert case["heartbeat"]["state"] == "dormant"
    for key in ("coverage", "case_value", "bills", "adherence", "other_care"):
        assert key not in case, key
    assert case["requests"] == [] and case["documents"] == []


def test_malformed_fact_is_ignored_not_fatal(seeded):
    with connect(seeded) as db:
        db.execute("INSERT INTO facts(matter_id, kind, value, citations, input_hash, created_at) "
                   "VALUES (?, 'coverage', '{\"carrier\": 1}', '[]', 'x', '2999-01-01T00:00:00Z')", (MATTER,))
        assert sources.coverage(db, MATTER) is None
    assert "coverage" not in _case(seeded, ["coverage"])
```

- [ ] **Step 2: Run, expect failure**

Run: `uv run pytest backend/tests/test_sharing.py -q`
Expected: FAIL. `AttributeError: module 'backend.app.sharing' has no attribute 'projection'` (ImportError).

- [ ] **Step 3: Implement the adapter**

Replace `backend/app/sharing/sources.py`:
```python
"""[Dev 2] Read-only adapter over Dev 1's tables: the ONLY sharing module that knows their schema.

Agreed shapes: docs/workstreams/interface-dev1-dev2.md. Every reader returns None / [] when data is missing
(no sync or digest yet, or a malformed fact), so the projection omits that section instead of failing.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from ..config import settings
from ..contracts import (BillLine, Coverage, Movement, NotFound, ProviderBills, ProviderIdentity, SharedDocument,
                         StageShare, WorthEstimate)
from ..db import jload


def data_dir() -> Path:
    """Root that records.meta.file_path is relative to (patched in tests)."""
    return settings.data_dir


def matter(db: sqlite3.Connection, matter_id: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM matters WHERE id = ?", (matter_id,)).fetchone()


def patient_display(db: sqlite3.Connection, matter_id: int) -> str:
    """Client initials ("J. R."); the full name never leaves the server."""
    row = db.execute("SELECT c.name FROM matters m JOIN contacts c ON c.id = m.client_id WHERE m.id = ?",
                     (matter_id,)).fetchone()
    parts = (row["name"] or "").replace(",", " ").split() if row else []
    return " ".join(f"{p[0].upper()}." for p in parts[:2]) or "Patient"


def stage(db: sqlite3.Connection, matter_id: int) -> StageShare | None:
    m = matter(db, matter_id)
    if m is None or not m["stage_name"]:
        return None
    names = [r["name"] for r in db.execute(
        "SELECT name FROM matter_stages WHERE ? IS NULL OR practice_area IS ? ORDER BY sort_order, id",
        (m["practice_area"], m["practice_area"]))]
    return StageShare(current=m["stage_name"], stages=names,
                      index=names.index(m["stage_name"]) if m["stage_name"] in names else None)


def last_activity_at(db: sqlite3.Connection, matter_id: int, until: str) -> str | None:
    """Most recent past record date (future due dates don't count as activity)."""
    return db.execute("SELECT MAX(occurred_at) AS at FROM records WHERE matter_id = ? AND deleted_at IS NULL "
                      "AND occurred_at IS NOT NULL AND occurred_at <= ?", (matter_id, until)).fetchone()["at"]


def movements(db: sqlite3.Connection, matter_id: int, until: str, limit: int = 5) -> list[Movement]:
    rows = db.execute(
        "SELECT r.occurred_at, d.provider_safe_summary AS text FROM records r JOIN digests d ON d.record_id = r.id "
        "WHERE r.matter_id = ? AND r.deleted_at IS NULL AND r.occurred_at IS NOT NULL AND r.occurred_at <= ? "
        "AND d.confidential = 0 AND COALESCE(d.provider_safe_summary, '') != '' "
        "ORDER BY r.occurred_at DESC LIMIT ?", (matter_id, until, limit))
    return [Movement(date=r["occurred_at"][:10], text=r["text"]) for r in rows]


def provider_identity(db: sqlite3.Connection, contact_id: int) -> ProviderIdentity | None:
    row = db.execute("SELECT id, name, email FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    return ProviderIdentity(contact_id=row["id"], name=row["name"] or "Provider", email=row["email"]) if row else None


def provider_bills(db: sqlite3.Connection, matter_id: int, contact_id: int) -> ProviderBills | None:
    rows = db.execute("SELECT title, occurred_at, meta FROM records WHERE matter_id = ? AND type = 'medical_bill' "
                      "AND deleted_at IS NULL AND json_extract(meta, '$.provider_contact_id') = ? ORDER BY occurred_at",
                      (matter_id, contact_id)).fetchall()
    if not rows:
        return None
    metas = [jload(r["meta"], {}) for r in rows]
    balances = [float(m["balance"]) for m in metas if m.get("balance") is not None]
    return ProviderBills(
        billed=sum(float(m.get("amount") or 0) for m in metas),
        balance=sum(balances) if balances else None,
        lien=any(bool(m.get("lien")) for m in metas),
        items=[BillLine(date=(r["occurred_at"] or "")[:10] or None, amount=float(m.get("amount") or 0),
                        description=m.get("description") or r["title"]) for r, m in zip(rows, metas)])


def documents(db: sqlite3.Connection, matter_id: int) -> list[SharedDocument]:
    rows = db.execute("SELECT r.id, r.title, (SELECT COUNT(*) FROM document_pages p WHERE p.document_id = r.id) AS pages "
                      "FROM records r WHERE r.matter_id = ? AND r.type = 'document' AND r.deleted_at IS NULL "
                      "ORDER BY r.occurred_at DESC, r.id", (matter_id,))
    return [SharedDocument(id=r["id"], title=r["title"] or "Document", page_count=r["pages"] or None) for r in rows]


def document_path(db: sqlite3.Connection, matter_id: int, document_id: str) -> Path | None:
    row = db.execute("SELECT meta FROM records WHERE id = ? AND matter_id = ? AND type = 'document' "
                     "AND deleted_at IS NULL", (document_id, matter_id)).fetchone()
    rel = jload(row["meta"], {}).get("file_path") if row else None
    if not rel:
        return None
    root = data_dir().resolve()
    path = (root / rel).resolve()
    return path if path.is_relative_to(root) and path.is_file() else None


def provider_request_rows(db: sqlite3.Connection, matter_id: int, contact_id: int) -> list[sqlite3.Row]:
    return db.execute("SELECT * FROM provider_requests WHERE matter_id = ? AND provider_contact_id = ? "
                      "ORDER BY requested_at DESC, id", (matter_id, contact_id)).fetchall()


def provider_request(db: sqlite3.Connection, request_id: str) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM provider_requests WHERE id = ?", (request_id,)).fetchone()


def _latest_fact(db: sqlite3.Connection, matter_id: int, kind: str):
    row = db.execute("SELECT value FROM facts WHERE matter_id = ? AND kind = ? ORDER BY created_at DESC, id DESC "
                     "LIMIT 1", (matter_id, kind)).fetchone()
    return jload(row["value"]) if row else None


def coverage(db: sqlite3.Connection, matter_id: int) -> Coverage | None:
    raw = _latest_fact(db, matter_id, "coverage")
    if raw is None:
        return None
    try:
        return Coverage.model_validate(raw)
    except ValidationError as e:
        print(f"[sharing] ignoring malformed coverage fact for matter {matter_id}: {e.error_count()} errors")
        return None


_WORTH = TypeAdapter(WorthEstimate | NotFound)


def worth(db: sqlite3.Connection, matter_id: int) -> WorthEstimate | None:
    raw = _latest_fact(db, matter_id, "worth")
    if raw is None:
        return None
    try:
        parsed = _WORTH.validate_python(raw)
    except ValidationError as e:
        print(f"[sharing] ignoring malformed worth fact for matter {matter_id}: {e.error_count()} errors")
        return None
    return parsed if isinstance(parsed, WorthEstimate) else None


def treatment_visits(db: sqlite3.Connection, matter_id: int) -> list[dict]:
    rows = db.execute("SELECT value FROM facts WHERE matter_id = ? AND kind = 'treatment_visit'", (matter_id,))
    return [v for v in (jload(r["value"], {}) for r in rows) if isinstance(v, dict) and v.get("date")]
```

- [ ] **Step 4: Implement requests + projection**

`backend/app/sharing/requests.py`:
```python
"""[Dev 2] Provider request view + app-local state (F7). State lives in request_states; never Clio."""
from __future__ import annotations

import sqlite3
from typing import Literal

from ..contracts import ProviderRequest
from ..db import jload, now_iso
from . import sources


def requests_for(db: sqlite3.Connection, matter_id: int, provider_contact_id: int, *,
                 audience: Literal["attorney", "provider"]) -> list[ProviderRequest]:
    rows = sources.provider_request_rows(db, matter_id, provider_contact_id)
    if not rows:
        return []
    marks = ",".join("?" * len(rows))
    states = {r["request_id"]: r["state"] for r in db.execute(
        f"SELECT request_id, state FROM request_states WHERE request_id IN ({marks})", [r["id"] for r in rows])}
    return [ProviderRequest(
        id=r["id"], kind=r["kind"], description=r["description"],
        requested_at=(r["requested_at"] or "")[:10] or None, channel=r["channel"],
        state=states.get(r["id"], "open"), provider_contact_id=r["provider_contact_id"],
        # Attorneys always see the source; providers only when the source message was addressed to them.
        citations=jload(r["citations"], []) if audience == "attorney" or r["source_addressed_to_provider"] else [],
    ) for r in rows]


def set_state(db: sqlite3.Connection, request_id: str, state: str, user_id: int) -> None:
    db.execute("INSERT INTO request_states(request_id, state, by_user_id, at) VALUES (?,?,?,?) "
               "ON CONFLICT(request_id) DO UPDATE SET state = excluded.state, by_user_id = excluded.by_user_id, "
               "at = excluded.at", (request_id, state, user_id, now_iso()))
```

`backend/app/sharing/projection.py`:
```python
"""[Dev 2] ProviderProjection: the ONLY code path that produces provider-visible data.

build_sections() computes everything one provider COULD see (already scoped to them). project() is a whitelist that
starts from the identity fields and copies a section only if the policy grants it. Share-candidates is project() with
every field granted, so the composer preview and the real provider page come from the same code.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import get_args

from ..config import settings
from ..contracts import (Adherence, CaseValueShare, Coverage, CoverageShare, Heartbeat, HeartbeatState, Movement,
                         OtherCare, ProviderBills, ProviderCase, ProviderRequest, SharedDocument, ShareField,
                         SharePolicy)
from ..db import now_iso
from . import requests, sources

ALL_FIELDS: list[str] = list(get_args(ShareField))
ACTIVE_DAYS, QUIET_DAYS, GAP_DAYS = 30, 90, 30


def heartbeat_state(matter_status: str | None, last_activity_at: str | None, today: date) -> HeartbeatState:
    if (matter_status or "").lower() == "closed":
        return "closed"
    if not last_activity_at:
        return "dormant"
    days = (today - date.fromisoformat(last_activity_at[:10])).days
    return "active" if days <= ACTIVE_DAYS else "quiet" if days <= QUIET_DAYS else "dormant"


@dataclass
class Sections:
    patient_display: str
    heartbeat: Heartbeat
    coverage_variants: dict[str, CoverageShare]
    case_value: CaseValueShare | None
    bills: ProviderBills | None
    requests: list[ProviderRequest]
    documents: list[SharedDocument]
    adherence: Adherence | None
    other_care: list[OtherCare]


def build_sections(db: sqlite3.Connection, matter_id: int, provider_contact_id: int) -> Sections:
    now = now_iso()
    today = date.fromisoformat(now[:10])
    m = sources.matter(db, matter_id)
    last = sources.last_activity_at(db, matter_id, now)
    moves = sources.movements(db, matter_id, now)
    last_move = moves[0] if moves else None
    if last and (last_move is None or last[:10] > last_move.date):
        last_move = Movement(date=last[:10], text="Case activity recorded")  # newest event is not provider-safe
    worth = sources.worth(db, matter_id)
    visits = sources.treatment_visits(db, matter_id)
    return Sections(
        patient_display=sources.patient_display(db, matter_id),
        heartbeat=Heartbeat(state=heartbeat_state(m["status"] if m else None, last, today),
                            last_activity_at=last[:10] if last else None, last_movement=last_move,
                            stage=sources.stage(db, matter_id), recent_movement=moves),
        coverage_variants=_coverage_variants(sources.coverage(db, matter_id)),
        case_value=CaseValueShare(low=worth.low, high=worth.high) if worth else None,
        bills=sources.provider_bills(db, matter_id, provider_contact_id),
        requests=requests.requests_for(db, matter_id, provider_contact_id, audience="provider"),
        documents=sources.documents(db, matter_id),
        adherence=_adherence(visits, provider_contact_id, today),
        other_care=_other_care(visits, provider_contact_id),
    )


def project(s: Sections, *, grant_id: int, policy: SharePolicy, shared_by: str | None) -> ProviderCase:
    granted = set(policy.fields)
    out: dict = dict(grant_id=grant_id, policy_version=policy.version, patient_display=s.patient_display,
                     firm_name=settings.firm_name, shared_by=shared_by, updated_at=policy.released_at,
                     status_note=policy.status_note or None)
    if "status" in granted:
        out["heartbeat"] = s.heartbeat
    if "coverage" in granted:
        out["coverage"] = s.coverage_variants.get(policy.coverage_detail)
    if "case_value" in granted:
        out["case_value"] = s.case_value
    if "bills" in granted:
        out["bills"] = s.bills
    if "open_requests" in granted:
        out["requests"] = [r for r in s.requests if r.state != "dismissed"]
    if "documents" in granted:
        allowed = set(policy.document_ids)
        out["documents"] = [d.model_copy(update={"shared_at": policy.released_at}) for d in s.documents
                            if d.id in allowed]
    if "adherence" in granted:
        out["adherence"] = s.adherence
    if "other_care" in granted:
        out["other_care"] = s.other_care or None
    return ProviderCase(**out)


def preview_policy(grant_id: int, documents: list[SharedDocument]) -> SharePolicy:
    """Everything granted: share-candidates uses it so the composer can filter the same projection client-side."""
    return SharePolicy(grant_id=grant_id, version=0, fields=ALL_FIELDS, document_ids=[d.id for d in documents],
                       coverage_detail="limits", released_at=now_iso())


def _coverage_variants(cov: Coverage | None) -> dict[str, CoverageShare]:
    if cov is None:
        return {}
    found = [(label, getattr(f, "value", None)) for label, f in (
        ("BI per person", cov.bi_per_person), ("BI per accident", cov.bi_per_accident),
        ("UM/UIM", cov.um_uim), ("MedPay", cov.medpay))]
    return {"confirmed": CoverageShare(confirmed=cov.confirmed),
            "limits": CoverageShare(confirmed=cov.confirmed, carrier=getattr(cov.carrier, "value", None),
                                    limits_text=" · ".join(f"{label} {v}" for label, v in found if v) or None)}


def _adherence(visits: list[dict], contact_id: int, today: date) -> Adherence | None:
    dates = sorted({v["date"][:10] for v in visits if v.get("provider_contact_id") == contact_id})
    if not dates:
        return None
    ds = [date.fromisoformat(d) for d in dates]
    gaps = [{"from": a.isoformat(), "to": b.isoformat(), "days": (b - a).days}
            for a, b in zip(ds, ds[1:]) if (b - a).days > GAP_DAYS]
    return Adherence(visits=dates, gaps=gaps, current_gap_days=(today - ds[-1]).days)


def _other_care(visits: list[dict], contact_id: int) -> list[OtherCare]:
    by_name: dict[str, list[str]] = {}
    for v in visits:
        if v.get("provider_contact_id") != contact_id and v.get("provider_name"):
            by_name.setdefault(v["provider_name"], []).append(v["date"][:10])
    return [OtherCare(provider_name=n, first_visit=min(d), last_visit=max(d)) for n, d in sorted(by_name.items())]
```

- [ ] **Step 5: Run, expect pass**

Run: `uv run pytest backend/tests/test_sharing.py -q`
Expected: all pass (6 invite + 10 projection). Then `uv run pytest -q` → the whole suite is green (Dev 1's `test_contracts.py` included).

- [ ] **Step 6: Commit**

```bash
git add backend/app/sharing backend/tests/test_sharing.py
git commit -m "feat(product): ProviderProjection whitelist + read-only Dev 1 adapter + request view (F6/F7)"
```

---

### Task 9: Grants, release, revoke, audit, candidates, attorney request routes (PLAN 2.6b, F5/F7/F8)

**Files:**
- Create: `backend/app/sharing/grants.py`
- Modify: `backend/app/api/shares.py` (replace every stub)
- Delete: `fixtures/{share_candidates,grants,grant,release_result,share_audit}.json`
- Test: `backend/tests/test_sharing.py` (append)

**Interfaces:**
- Consumes: `events`, `invites`, `sources`, `projection`, `requests`
- Produces:
  - `grants.get_grant(db, id) -> Row` (404), `latest_policy(db, id) -> SharePolicy | None`, `policies(db, id)`, `grant_out(db, row) -> Grant`, `list_grants(db, matter_id)`, `create_grant(db, body, user) -> Grant`, `release(db, grant_id, body, user) -> ReleaseResult`, `revoke(db, grant_id, user)`, `audit(db, grant_id) -> ShareAudit`, `candidates(db, matter_id, contact_id) -> ShareCandidates`
  - Routes (attorney): `GET /api/matters/{matter_id}/share-candidates?provider_contact_id=`, `GET /api/matters/{matter_id}/shares`, `POST /api/shares`, `POST /api/shares/{grant_id}/release`, `POST /api/shares/{grant_id}/revoke`, `GET /api/shares/{grant_id}/audit`, `POST /api/requests/{request_id}/dismiss`, `GET /api/matters/{matter_id}/requests?provider_contact_id=`

- [ ] **Step 1: Failing tests (append)**

```python
# ------------------------------------------------------------------------------ grants / release / audit (2.6b)


def test_release_versions_and_logs(api, seeded):
    att = api("attorney")
    gid, r1 = share(att, fields=["status"])
    assert r1["policy"]["version"] == 1 and r1["invite_url"] is None        # provider A already has an account
    _, r2 = share(att, fields=["status", "coverage"])                        # same grant reused
    assert r2["policy"]["version"] == 2
    audit = att.get(f"/api/shares/{gid}/audit").json()
    assert [v["policy"]["version"] for v in audit["versions"]] == [1, 2]
    assert audit["versions"][1]["added"] == ["coverage", "coverage:confirmed"] and audit["versions"][1]["removed"] == []
    assert [e["event"] for e in audit["events"]] == ["released", "released"]
    assert audit["grant"]["latest_version"] == 2 and audit["grant"]["provider_user_id"] is not None


def test_release_to_new_email_creates_invite(api, seeded, capsys):
    att = api("attorney")
    gid, r = share(att, contact=PROV_B, email="new@clinic.test")
    assert r["invite_url"] and "/invite/" in r["invite_url"]
    assert r["invite_url"] in capsys.readouterr().out                       # console fallback
    events = [e["event"] for e in att.get(f"/api/shares/{gid}/audit").json()["events"]]
    assert events == ["released", "invite_sent"]


def test_release_rejects_foreign_documents_and_revoked_grants(api, seeded):
    att = api("attorney")
    gid, _ = share(att)
    bad = att.post(f"/api/shares/{gid}/release", json={"fields": ["documents"], "document_ids": ["document:999"]})
    assert bad.status_code == 400
    assert att.post(f"/api/shares/{gid}/revoke").status_code == 200
    again = att.post(f"/api/shares/{gid}/release", json={"fields": ["status"]})
    assert again.status_code == 409
    assert att.get(f"/api/shares/{gid}/audit").json()["events"][-1]["event"] == "revoked"


def test_candidates_include_everything_scoped(api, seeded):
    att = api("attorney")
    c = att.get(f"/api/matters/{MATTER}/share-candidates?provider_contact_id={PROV_A}").json()
    assert c["provider"]["name"] == "Provider A Clinic"
    assert set(c["coverage_variants"]) == {"confirmed", "limits"}
    assert {d["id"] for d in c["available_documents"]} == {"document:10", "document:11"}
    assert c["case"]["bills"]["billed"] == 1200.0 and "heartbeat" in c["case"]


def test_candidates_for_unknown_provider_404(api, seeded):
    assert api("attorney").get(f"/api/matters/{MATTER}/share-candidates?provider_contact_id=999").status_code == 404


def test_attorney_request_view_and_dismiss(api, seeded):
    att = api("attorney")
    gid, _ = share(att, fields=["open_requests"])
    reqs = att.get(f"/api/matters/{MATTER}/requests?provider_contact_id={PROV_A}").json()
    assert all(r["citations"] for r in reqs)                                  # attorney always sees sources
    assert att.post("/api/requests/req:1/dismiss").status_code == 200
    states = {r["id"]: r["state"] for r in att.get(f"/api/matters/{MATTER}/requests?provider_contact_id={PROV_A}").json()}
    assert states["req:1"] == "dismissed"
    assert att.get(f"/api/shares/{gid}/audit").json()["events"][-1]["event"] == "request_dismissed"
    assert att.post("/api/requests/req:nope/dismiss").status_code == 404


def test_list_grants(api, seeded):
    att = api("attorney")
    share(att)
    grants = att.get(f"/api/matters/{MATTER}/shares").json()
    assert len(grants) == 1 and grants[0]["provider_name"] == "Provider A Clinic"
```

- [ ] **Step 2: Run, expect failure**

Run: `uv run pytest backend/tests/test_sharing.py -q -k "release or candidates or request_view or list_grants"`
Expected: FAIL. Stub fixtures come back (wrong versions/ids, or `KeyError`).

- [ ] **Step 3: Implement grants service**

`backend/app/sharing/grants.py`:
```python
"""[Dev 2] Share grants + versioned policies: create, release (→ invite), revoke, audit, candidates (F5, F8)."""
from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from ..contracts import (CreateGrantRequest, Grant, PolicyVersionDiff, ReleaseRequest, ReleaseResult, ShareAudit,
                         ShareCandidates, SharePolicy)
from ..db import jdump, jload, now_iso
from . import events, invites, projection, sources

_POLICY_SQL = ("SELECT p.*, COALESCE(u.name, u.email) AS released_by_name FROM share_policies p "
               "LEFT JOIN users u ON u.id = p.released_by WHERE p.grant_id = ?")


def get_grant(db: sqlite3.Connection, grant_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM share_grants WHERE id = ?", (grant_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Share not found")
    return row


def _policy(row: sqlite3.Row) -> SharePolicy:
    return SharePolicy(grant_id=row["grant_id"], version=row["version"], fields=jload(row["fields"], []),
                       document_ids=jload(row["document_ids"], []), coverage_detail=row["coverage_detail"],
                       status_note=row["status_note"], released_by=row["released_by_name"],
                       released_at=row["released_at"])


def policies(db: sqlite3.Connection, grant_id: int) -> list[SharePolicy]:
    return [_policy(r) for r in db.execute(_POLICY_SQL + " ORDER BY p.version", (grant_id,))]


def latest_policy(db: sqlite3.Connection, grant_id: int) -> SharePolicy | None:
    row = db.execute(_POLICY_SQL + " ORDER BY p.version DESC LIMIT 1", (grant_id,)).fetchone()
    return _policy(row) if row else None


def grant_out(db: sqlite3.Connection, row: sqlite3.Row) -> Grant:
    latest = latest_policy(db, row["id"])
    views = db.execute("SELECT COUNT(*) AS n, MAX(at) AS last FROM share_events WHERE grant_id = ? AND event = 'viewed'",
                       (row["id"],)).fetchone()
    return Grant(id=row["id"], matter_id=row["matter_id"], provider_contact_id=row["provider_contact_id"],
                 provider_name=row["provider_name"], email=row["email"], provider_user_id=row["provider_user_id"],
                 latest_version=latest.version if latest else None,
                 released_at=latest.released_at if latest else None, revoked_at=row["revoked_at"],
                 last_viewed_at=views["last"], view_count=views["n"])


def list_grants(db: sqlite3.Connection, matter_id: int) -> list[Grant]:
    return [grant_out(db, r) for r in db.execute("SELECT * FROM share_grants WHERE matter_id = ? ORDER BY id",
                                                 (matter_id,))]


def _active_grant(db: sqlite3.Connection, matter_id: int, contact_id: int) -> sqlite3.Row | None:
    return db.execute("SELECT * FROM share_grants WHERE matter_id = ? AND provider_contact_id = ? "
                      "AND revoked_at IS NULL ORDER BY id DESC LIMIT 1", (matter_id, contact_id)).fetchone()


def create_grant(db: sqlite3.Connection, body: CreateGrantRequest, user: sqlite3.Row) -> Grant:
    """Idempotent per (matter, provider): returns the active grant if one exists."""
    row = _active_grant(db, body.matter_id, body.provider_contact_id)
    if row is None:
        ident = sources.provider_identity(db, body.provider_contact_id)
        cur = db.execute("INSERT INTO share_grants(matter_id, provider_contact_id, provider_name, email, created_by, "
                         "created_at) VALUES (?,?,?,?,?,?)",
                         (body.matter_id, body.provider_contact_id, ident.name if ident else None,
                          body.email.strip().lower(), user["id"], now_iso()))
        row = get_grant(db, int(cur.lastrowid))
    return grant_out(db, row)


def release(db: sqlite3.Connection, grant_id: int, body: ReleaseRequest, user: sqlite3.Row) -> ReleaseResult:
    grant = get_grant(db, grant_id)
    if grant["revoked_at"]:
        raise HTTPException(409, "This share was revoked; create a new one")
    unknown = set(body.document_ids) - {d.id for d in sources.documents(db, grant["matter_id"])}
    if unknown:
        raise HTTPException(400, f"Not documents of this matter: {sorted(unknown)}")
    fields, docs = list(dict.fromkeys(body.fields)), list(dict.fromkeys(body.document_ids))
    version = db.execute("SELECT COALESCE(MAX(version), 0) + 1 AS v FROM share_policies WHERE grant_id = ?",
                         (grant_id,)).fetchone()["v"]
    db.execute("INSERT INTO share_policies(grant_id, version, fields, document_ids, coverage_detail, status_note, "
               "released_by, released_at) VALUES (?,?,?,?,?,?,?,?)",
               (grant_id, version, jdump(fields), jdump(docs), body.coverage_detail,
                (body.status_note or "").strip() or None, user["id"], now_iso()))
    events.log_event(db, grant_id, "released", user, version=version, meta={"fields": fields, "document_ids": docs})
    invite_url = None
    if grant["provider_user_id"] is None:
        existing = db.execute("SELECT id FROM users WHERE email = ? AND role = 'provider'",
                              (grant["email"],)).fetchone()
        if existing:   # provider already has an account (e.g. from another matter): attach, no invite needed
            db.execute("UPDATE share_grants SET provider_user_id = ? WHERE id = ?", (existing["id"], grant_id))
        else:
            invite_url = invites.invite_url(invites.create_invite(db, grant["email"], grant_id))
            invites.deliver(grant["email"], invite_url)
            events.log_event(db, grant_id, "invite_sent", user, version=version, meta={"email": grant["email"]})
    return ReleaseResult(policy=latest_policy(db, grant_id), invite_url=invite_url)


def revoke(db: sqlite3.Connection, grant_id: int, user: sqlite3.Row) -> None:
    grant = get_grant(db, grant_id)
    if grant["revoked_at"] is None:
        db.execute("UPDATE share_grants SET revoked_at = ? WHERE id = ?", (now_iso(), grant_id))
        latest = latest_policy(db, grant_id)
        events.log_event(db, grant_id, "revoked", user, version=latest.version if latest else None)


def _diff_keys(p: SharePolicy) -> set[str]:
    keys = set(p.fields) | set(p.document_ids)
    if "coverage" in p.fields:
        keys.add(f"coverage:{p.coverage_detail}")
    return keys


def audit(db: sqlite3.Connection, grant_id: int) -> ShareAudit:
    grant = get_grant(db, grant_id)
    versions, prev = [], set()
    for p in policies(db, grant_id):
        keys = _diff_keys(p)
        versions.append(PolicyVersionDiff(policy=p, added=sorted(keys - prev), removed=sorted(prev - keys)))
        prev = keys
    return ShareAudit(grant=grant_out(db, grant), versions=versions, events=events.events_for(db, grant_id))


def candidates(db: sqlite3.Connection, matter_id: int, provider_contact_id: int) -> ShareCandidates:
    ident = sources.provider_identity(db, provider_contact_id)
    if ident is None:
        raise HTTPException(404, "Provider not found")
    s = projection.build_sections(db, matter_id, provider_contact_id)
    active = _active_grant(db, matter_id, provider_contact_id)
    grant_id = active["id"] if active else 0
    case = projection.project(s, grant_id=grant_id, policy=projection.preview_policy(grant_id, s.documents),
                              shared_by=None)
    return ShareCandidates(provider=ident, case=case, coverage_variants=s.coverage_variants,
                           available_documents=s.documents)
```

- [ ] **Step 4: Replace the shares router**

`backend/app/api/shares.py`:
```python
"""[Dev 2] Share grants, versioned policies, candidates, audit, attorney request actions (F5, F7, F8)."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_user, require_role
from ..contracts import (CreateGrantRequest, Grant, OkResponse, ProviderRequest, ReleaseRequest, ReleaseResult,
                         ShareAudit, ShareCandidates)
from ..db import get_db
from ..sharing import events, grants, requests, sources

router = APIRouter(prefix="/api", tags=["shares"], dependencies=[Depends(require_role("attorney"))])


@router.get("/matters/{matter_id}/share-candidates", response_model=ShareCandidates,
            response_model_exclude_none=True)
def share_candidates(matter_id: int, provider_contact_id: int, db: sqlite3.Connection = Depends(get_db)):
    return grants.candidates(db, matter_id, provider_contact_id)


@router.get("/matters/{matter_id}/shares", response_model=list[Grant])
def list_grants(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    return grants.list_grants(db, matter_id)


@router.get("/matters/{matter_id}/requests", response_model=list[ProviderRequest])
def provider_requests(matter_id: int, provider_contact_id: int, db: sqlite3.Connection = Depends(get_db)):
    return requests.requests_for(db, matter_id, provider_contact_id, audience="attorney")


@router.post("/shares", response_model=Grant)
def create_grant(body: CreateGrantRequest, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    return grants.create_grant(db, body, user)


@router.post("/shares/{grant_id}/release", response_model=ReleaseResult)
def release(grant_id: int, body: ReleaseRequest, db: sqlite3.Connection = Depends(get_db),
            user=Depends(current_user)):
    return grants.release(db, grant_id, body, user)


@router.post("/shares/{grant_id}/revoke", response_model=OkResponse)
def revoke(grant_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    grants.revoke(db, grant_id, user)
    return OkResponse()


@router.get("/shares/{grant_id}/audit", response_model=ShareAudit)
def audit(grant_id: int, db: sqlite3.Connection = Depends(get_db)):
    return grants.audit(db, grant_id)


@router.post("/requests/{request_id}/dismiss", response_model=OkResponse)
def dismiss_request(request_id: str, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    req = sources.provider_request(db, request_id)
    if req is None:
        raise HTTPException(404, "Request not found")
    requests.set_state(db, request_id, "dismissed", user["id"])
    for g in db.execute("SELECT id FROM share_grants WHERE matter_id = ? AND provider_contact_id = ? "
                        "AND revoked_at IS NULL", (req["matter_id"], req["provider_contact_id"])).fetchall():
        latest = grants.latest_policy(db, g["id"])
        events.log_event(db, g["id"], "request_dismissed", user, version=latest.version if latest else None,
                         meta={"request_id": request_id})
    return OkResponse()
```

- [ ] **Step 5: Delete Dev 2 fixtures for these endpoints**

```bash
git rm fixtures/share_candidates.json fixtures/grants.json fixtures/grant.json fixtures/release_result.json fixtures/share_audit.json
grep -rn "share_candidates\|release_result\|share_audit\|\"grants\"\|\"grant\"" backend/app || echo "no references left"
```

- [ ] **Step 6: Run, expect pass**

Run: `uv run pytest -q`
Expected: all green. Then `make backend` must start (deny-by-default check passes).

- [ ] **Step 7: Commit**

```bash
git add -A backend/app/sharing backend/app/api/shares.py backend/tests/test_sharing.py fixtures
git commit -m "feat(product): share grants, versioned release + invite, revoke, audit diffs, candidates, request dismiss (F5/F7/F8)"
```

---

### Task 10: Provider endpoints + RBAC suite (PLAN 2.6c, F6/F7/F8)

**Files:**
- Create: `backend/app/sharing/access.py`, `backend/tests/test_rbac.py`
- Modify: `backend/app/api/provider.py` (replace stubs)
- Delete: `fixtures/{provider_case,provider_cases}.json`
- Test: `backend/tests/test_sharing.py` (append event-order + mark-sent tests)

**Interfaces:**
- Consumes: `grants.latest_policy`, `projection`, `requests`, `events`, `sources.document_path`
- Produces:
  - `access.owned_grant(db, grant_id, user) -> (Row, SharePolicy)` (404 otherwise), `access.case_for(db, grant, policy) -> ProviderCase`, `access.summaries(db, user) -> list[ProviderCaseSummary]`
  - Routes (provider): `GET /api/provider/cases`, `GET /api/provider/cases/{grant_id}` (logs `viewed`), `GET /api/provider/cases/{grant_id}/documents/{document_id}` (logs `document_opened`), `POST /api/provider/requests/{request_id}/complete`

- [ ] **Step 1: Failing tests**

`backend/tests/test_rbac.py`:
```python
"""[Dev 2] RBAC: role walls on EVERY route (auto-discovered, so Dev 1's routes are covered too), provider isolation."""
import re

from fastapi.routing import APIRoute

from backend.app.main import app
from backend.tests.dev2_support import EMAILS, MATTER, PROV_B, api, db_path, seeded, share  # noqa: F401


def _roles(dependant) -> set[str]:
    roles: set[str] = set()
    for d in dependant.dependencies:
        roles |= set(getattr(d.call, "__role_guard__", ()))
        roles |= _roles(d)
    return roles


def _routes(role: str) -> list[tuple[str, str]]:
    out = []
    for r in app.routes:
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
```

Append to `backend/tests/test_sharing.py`:
```python
# ----------------------------------------------------------------------------------- provider flow (2.6c, F6–F8)


def test_release_view_open_events_in_order(api, seeded):
    att = api("attorney")
    gid, _ = share(att, fields=["status", "documents"], docs=["document:10"])
    a = api("a")
    case = a.get(f"/api/provider/cases/{gid}")
    assert case.status_code == 200 and "coverage" not in case.json() and "bills" not in case.json()
    doc = a.get(f"/api/provider/cases/{gid}/documents/document:10")
    assert doc.status_code == 200 and doc.content.startswith(b"%PDF")
    events = att.get(f"/api/shares/{gid}/audit").json()["events"]
    assert [e["event"] for e in events] == ["released", "viewed", "document_opened"]
    assert events[1]["actor_email"] == EMAILS["a"] and events[2]["meta"]["document_id"] == "document:10"


def test_provider_reload_reflects_new_version(api, seeded):
    att = api("attorney")
    gid, _ = share(att, fields=["status"])
    a = api("a")
    assert a.get(f"/api/provider/cases/{gid}").json()["policy_version"] == 1
    share(att, fields=["status", "bills"])
    v2 = a.get(f"/api/provider/cases/{gid}").json()
    assert v2["policy_version"] == 2 and v2["bills"]["billed"] == 1200.0


def test_mark_sent_persists_and_logs(api, seeded):
    att = api("attorney")
    gid, _ = share(att, fields=["open_requests"])
    a = api("a")
    assert a.post("/api/provider/requests/req:1/complete").status_code == 200
    reqs = {r["id"]: r for r in a.get(f"/api/provider/cases/{gid}").json()["requests"]}
    assert reqs["req:1"]["state"] == "completed"
    assert att.get(f"/api/shares/{gid}/audit").json()["events"][-1]["event"] == "request_completed"


def test_mark_sent_requires_open_requests_shared(api, seeded):
    att = api("attorney")
    share(att, fields=["status"])
    assert api("a").post("/api/provider/requests/req:1/complete").status_code == 404


def test_case_list_respects_whitelist(api, seeded):
    att = api("attorney")
    share(att, fields=["documents"])          # no status, no open_requests
    [summary] = api("a").get("/api/provider/cases").json()
    assert summary["patient_display"] == "P. E."
    assert summary.get("state") is None and summary["open_requests"] == 0
```

- [ ] **Step 2: Run, expect failure**

Run: `uv run pytest backend/tests/test_rbac.py backend/tests/test_sharing.py -q`
Expected: FAIL (provider stubs return fixtures / 404 for documents).

- [ ] **Step 3: Implement access + provider router**

`backend/app/sharing/access.py`:
```python
"""[Dev 2] Provider-side access: ownership filter on every query. Anything not theirs → 404 (never 403),
so grant ids can't be probed."""
from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from ..contracts import ProviderCase, ProviderCaseSummary, SharePolicy
from . import grants, projection


def owned_grant(db: sqlite3.Connection, grant_id: int, user: sqlite3.Row) -> tuple[sqlite3.Row, SharePolicy]:
    grant = db.execute("SELECT * FROM share_grants WHERE id = ? AND provider_user_id = ? AND revoked_at IS NULL",
                       (grant_id, user["id"])).fetchone()
    policy = grants.latest_policy(db, grant_id) if grant else None
    if grant is None or policy is None:
        raise HTTPException(404, "Case not found")
    return grant, policy


def case_for(db: sqlite3.Connection, grant: sqlite3.Row, policy: SharePolicy) -> ProviderCase:
    sections = projection.build_sections(db, grant["matter_id"], grant["provider_contact_id"])
    return projection.project(sections, grant_id=grant["id"], policy=policy, shared_by=policy.released_by)


def summaries(db: sqlite3.Connection, user: sqlite3.Row) -> list[ProviderCaseSummary]:
    out = []
    for g in db.execute("SELECT * FROM share_grants WHERE provider_user_id = ? AND revoked_at IS NULL ORDER BY id DESC",
                        (user["id"],)).fetchall():
        policy = grants.latest_policy(db, g["id"])
        if policy is None:
            continue
        case = case_for(db, g, policy)          # derive from the projection so the whitelist applies here too
        hb = case.heartbeat
        out.append(ProviderCaseSummary(
            grant_id=g["id"], patient_display=case.patient_display, firm_name=case.firm_name,
            state=hb.state if hb else None, last_movement_at=hb.last_movement.date if hb and hb.last_movement else None,
            open_requests=sum(1 for r in case.requests or [] if r.state == "open")))
    return out
```

`backend/app/api/provider.py`:
```python
"""[Dev 2] Provider-role endpoints (F6, F7, F8). Output is ONLY ProviderProjection; every query is filtered by
grant ownership (404 otherwise); unshared sections are absent (exclude_none); views/doc opens are logged."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..auth import current_user, require_role
from ..contracts import OkResponse, ProviderCase, ProviderCaseSummary
from ..db import get_db
from ..sharing import access, events, grants, requests, sources

router = APIRouter(prefix="/api/provider", tags=["provider"], dependencies=[Depends(require_role("provider"))])


@router.get("/cases", response_model=list[ProviderCaseSummary])
def my_cases(db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    return access.summaries(db, user)


@router.get("/cases/{grant_id}", response_model=ProviderCase, response_model_exclude_none=True)
def my_case(grant_id: int, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    grant, policy = access.owned_grant(db, grant_id, user)
    case = access.case_for(db, grant, policy)
    events.log_event(db, grant_id, "viewed", user, version=policy.version)
    return case


@router.get("/cases/{grant_id}/documents/{document_id}")
def my_document(grant_id: int, document_id: str, db: sqlite3.Connection = Depends(get_db),
                user=Depends(current_user)):
    grant, policy = access.owned_grant(db, grant_id, user)
    if "documents" not in policy.fields or document_id not in policy.document_ids:
        raise HTTPException(404, "Document not found")
    path = sources.document_path(db, grant["matter_id"], document_id)
    if path is None:
        raise HTTPException(404, "Document file not available")
    events.log_event(db, grant_id, "document_opened", user, version=policy.version,
                     meta={"document_id": document_id})
    return FileResponse(path)  # no filename → no attachment header → browser renders inline


@router.post("/requests/{request_id}/complete", response_model=OkResponse)
def complete_request(request_id: str, db: sqlite3.Connection = Depends(get_db), user=Depends(current_user)):
    req = sources.provider_request(db, request_id)
    grant = req and db.execute(
        "SELECT id FROM share_grants WHERE matter_id = ? AND provider_contact_id = ? AND provider_user_id = ? "
        "AND revoked_at IS NULL ORDER BY id DESC LIMIT 1",
        (req["matter_id"], req["provider_contact_id"], user["id"])).fetchone()
    policy = grant and grants.latest_policy(db, grant["id"])
    if not policy or "open_requests" not in policy.fields:
        raise HTTPException(404, "Request not found")
    requests.set_state(db, request_id, "completed", user["id"])
    events.log_event(db, grant["id"], "request_completed", user, version=policy.version,
                     meta={"request_id": request_id})
    return OkResponse()
```

- [ ] **Step 4: Delete provider fixtures**

```bash
git rm fixtures/provider_case.json fixtures/provider_cases.json
grep -rn "provider_case" backend/app/stubs.py backend/app/api || echo "clean"
```

- [ ] **Step 5: Run, expect pass**

Run: `uv run pytest -q`
Expected: all green, including `test_contracts.py`, and `make backend` boots.

Known pre-checkpoint smoke gap: `make smoke` asks for share-candidates for provider 600 (from Dev 1's stubbed `/providers`). On an empty `data/casepulse.db` that contact doesn't exist, so the row returns 404. That's expected until real data lands at the checkpoint. Every other smoke row should pass.

- [ ] **Step 6: Commit + push**

```bash
git add -A backend/app/sharing backend/app/api/provider.py backend/tests fixtures
git commit -m "feat(product): provider endpoints (ownership 404s, logged views/doc opens, mark sent) + RBAC suite"
git push
```

---

### Task 11: Provider components + provider app (PLAN 2.8, F6/F7)

Built before the composer because the composer preview reuses these components.

**Files:**
- Create: `frontend/components/provider/ProviderCaseView.tsx` (pure; composes sections), `frontend/lib/policy.ts`, `frontend/lib/policy.test.ts`
- Modify: `frontend/app/(provider)/provider/cases/page.tsx`, `frontend/app/(provider)/provider/cases/[grant]/page.tsx`

**Interfaces:**
- Consumes: types `ProviderCase`, `ProviderCaseSummary`, `ShareCandidates`, `ShareField`; `fmtDate`, `fmtMoney`, `daysAgo`, `apiUrl`
- Produces:
  - `<ProviderCaseView c onMarkSent? docHref? preview?/>`. Pure: no fetching, renders only keys that exist.
  - `applyPolicy(c: ShareCandidates, t: Toggles) -> ProviderCase`, `type Toggles = {fields: ShareField[]; document_ids: string[]; coverage_detail: "confirmed"|"limits"; status_note: string}`

- [ ] **Step 1: Failing test for `applyPolicy` (mirrors backend `project`)**

`frontend/lib/policy.test.ts`:
```ts
import { describe, expect, it } from "vitest";
import { applyPolicy, type Toggles } from "./policy";
import type { ShareCandidates } from "./types";

const candidates = {
  provider: { contact_id: 600, name: "Provider A" },
  coverage_variants: { confirmed: { confirmed: true }, limits: { confirmed: true, carrier: "Acme", limits_text: "BI per person $100,000" } },
  available_documents: [{ id: "document:10", title: "Report" }, { id: "document:11", title: "Memo" }],
  case: {
    grant_id: 0, policy_version: 0, patient_display: "P. E.", firm_name: "Firm",
    heartbeat: { state: "active", recent_movement: [] },
    coverage: { confirmed: true, carrier: "Acme", limits_text: "x" },
    case_value: { label: "Estimate", low: 1, high: 2 },
    bills: { billed: 10, lien: false, items: [] },
    requests: [{ id: "r1", kind: "records", description: "d", state: "open", citations: [] },
               { id: "r2", kind: "bills", description: "d", state: "dismissed", citations: [] }],
    documents: [{ id: "document:10", title: "Report" }, { id: "document:11", title: "Memo" }],
    adherence: { visits: ["2026-09-01"], gaps: [] },
    other_care: [],
  },
} as unknown as ShareCandidates;

const t = (o: Partial<Toggles>): Toggles => ({ fields: [], document_ids: [], coverage_detail: "confirmed", status_note: "", ...o });

describe("applyPolicy", () => {
  it("keeps only identity keys when nothing is toggled", () => {
    expect(Object.keys(applyPolicy(candidates, t({}))).sort()).toEqual(["firm_name", "grant_id", "patient_display", "policy_version"]);
  });
  it("adds exactly the toggled sections", () => {
    const c = applyPolicy(candidates, t({ fields: ["status", "bills"] }));
    expect(c.heartbeat?.state).toBe("active");
    expect(c.bills?.billed).toBe(10);
    expect("coverage" in c).toBe(false);
    expect("case_value" in c).toBe(false);
  });
  it("uses the chosen coverage variant", () => {
    expect(applyPolicy(candidates, t({ fields: ["coverage"] })).coverage).toEqual({ confirmed: true });
    expect(applyPolicy(candidates, t({ fields: ["coverage"], coverage_detail: "limits" })).coverage?.carrier).toBe("Acme");
  });
  it("filters documents to the picked ids and drops dismissed requests", () => {
    const c = applyPolicy(candidates, t({ fields: ["documents", "open_requests"], document_ids: ["document:11"] }));
    expect(c.documents?.map((d) => d.id)).toEqual(["document:11"]);
    expect(c.requests?.map((r) => r.id)).toEqual(["r1"]);
  });
  it("omits empty other-care and includes a trimmed status note", () => {
    const c = applyPolicy(candidates, t({ fields: ["other_care"], status_note: "  Hi  " }));
    expect("other_care" in c).toBe(false);
    expect(c.status_note).toBe("Hi");
  });
});
```

- [ ] **Step 2: Run, expect failure**

Run: `cd frontend && npm test -- policy` → FAIL (module missing).

- [ ] **Step 3: Implement `applyPolicy`**

`frontend/lib/policy.ts`:
```ts
/** Client mirror of backend sharing/projection.py:project(). Keep the two in lockstep; tests pin both. */
import type { ProviderCase, ShareCandidates, ShareField } from "./types";

export type Toggles = { fields: ShareField[]; document_ids: string[]; coverage_detail: "confirmed" | "limits"; status_note: string };

const SECTIONS = ["heartbeat", "coverage", "case_value", "bills", "requests", "documents", "adherence", "other_care", "status_note", "shared_by", "updated_at"] as const;

export function applyPolicy(c: ShareCandidates, t: Toggles): ProviderCase {
  const out: Record<string, unknown> = { ...c.case };
  for (const k of SECTIONS) delete out[k];
  const on = new Set(t.fields);
  const put = (k: string, v: unknown) => { if (v != null) out[k] = v; };
  put("status_note", t.status_note.trim() || null);
  if (on.has("status")) put("heartbeat", c.case.heartbeat);
  if (on.has("coverage")) put("coverage", c.coverage_variants[t.coverage_detail]);
  if (on.has("case_value")) put("case_value", c.case.case_value);
  if (on.has("bills")) put("bills", c.case.bills);
  if (on.has("open_requests")) put("requests", (c.case.requests ?? []).filter((r) => r.state !== "dismissed"));
  if (on.has("documents")) { const ids = new Set(t.document_ids); put("documents", c.available_documents.filter((d) => ids.has(d.id))); }
  if (on.has("adherence")) put("adherence", c.case.adherence);
  if (on.has("other_care")) put("other_care", c.case.other_care?.length ? c.case.other_care : null);
  return out as ProviderCase;
}
```

Run: `npm test` → PASS.

- [ ] **Step 4: Pure provider view**

`frontend/components/provider/ProviderCaseView.tsx`:
```tsx
/** Provider case page body. PURE (props in, no fetching) so the Share Composer preview renders the exact same thing.
 *  Renders only keys that exist; never shows "redacted". Must not import attorney components (ESLint enforces). */
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { daysAgo, fmtDate, fmtMoney } from "@/lib/format";
import type { ProviderCase } from "@/lib/types";

const DOT: Record<string, string> = { active: "bg-emerald-500", quiet: "bg-amber-500", dormant: "bg-slate-400", closed: "bg-slate-600" };

type Props = {
  c: ProviderCase;
  onMarkSent?: (requestId: string) => void;
  docHref?: (documentId: string) => string;
  preview?: boolean;
};

export function ProviderCaseView({ c, onMarkSent, docHref, preview }: Props) {
  const hb = c.heartbeat;
  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-lg font-semibold">Patient {c.patient_display}</h1>
        <p className="text-xs text-muted-foreground">shared by {c.shared_by ?? c.firm_name} · {c.firm_name}{!preview && ` · policy v${c.policy_version}`}</p>
      </div>
      {hb && (
        <Card><CardContent className="space-y-2 pt-4 text-sm">
          <p className="flex items-center gap-2 font-medium">
            <span className={`h-2.5 w-2.5 rounded-full ${DOT[hb.state]}`} /> {hb.state.toUpperCase()}
            {hb.last_movement && <span className="font-normal">· Last movement {fmtDate(hb.last_movement.date)}: “{hb.last_movement.text}”</span>}
          </p>
          {hb.stage?.stages?.length ? (
            <ol className="flex flex-wrap gap-1 text-[11px]">
              {hb.stage.stages.map((s, i) => <li key={s} className={`rounded px-2 py-0.5 ${hb.stage?.index != null && i <= hb.stage.index ? "bg-primary text-primary-foreground" : "bg-muted"}`}>{s}</li>)}
            </ol>
          ) : null}
        </CardContent></Card>
      )}
      {c.status_note && <Card><CardContent className="pt-4 text-sm">{c.status_note}</CardContent></Card>}
      {c.coverage && (
        <Section title="Coverage">
          {c.coverage.confirmed ? "✔ Coverage confirmed" : "Coverage not yet confirmed"}
          {c.coverage.carrier && <> · {c.coverage.carrier}</>}
          {c.coverage.limits_text && <p className="text-muted-foreground">{c.coverage.limits_text}</p>}
        </Section>
      )}
      {c.case_value && <Section title="Case value (estimate)">{fmtMoney(c.case_value.low)} – {fmtMoney(c.case_value.high)}</Section>}
      {c.requests && (
        <Section title="What the firm needs from you">
          {c.requests.length === 0 ? <p className="text-muted-foreground">Nothing outstanding.</p> : (
            <ul className="space-y-2">
              {c.requests.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center gap-2">
                  <span>{r.state === "completed" ? "☑" : "☐"} {r.description}</span>
                  <span className="text-xs text-muted-foreground">{r.requested_at && `requested ${fmtDate(r.requested_at)}`}{r.channel && ` by ${r.channel}`}</span>
                  {r.citations?.[0] && <blockquote className="w-full border-l-2 pl-2 text-xs italic">“{r.citations[0].excerpt}”</blockquote>}
                  {r.state === "open" && (
                    <Button size="sm" variant="outline" className="ml-auto" disabled={!onMarkSent} onClick={() => onMarkSent?.(r.id)}>Mark sent</Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}
      {c.bills && (
        <Section title="Your bills">
          {fmtMoney(c.bills.billed)} billed{c.bills.balance != null && ` · ${fmtMoney(c.bills.balance)} balance`}{c.bills.lien && " · lien on file"}
        </Section>
      )}
      {c.documents && (
        <Section title="Recently shared documents">
          {c.documents.length === 0 ? <p className="text-muted-foreground">No documents shared.</p> : (
            <ul className="space-y-1">
              {c.documents.map((d) => (
                <li key={d.id} className="flex items-center gap-2">
                  {d.title}{d.page_count && <span className="text-xs text-muted-foreground">({d.page_count} pp)</span>}
                  {d.shared_at && <span className="text-xs text-muted-foreground">· shared {fmtDate(d.shared_at)}</span>}
                  {docHref ? <a className="ml-auto text-sm underline" href={docHref(d.id)} target="_blank" rel="noreferrer">Open</a> : <span className="ml-auto text-xs text-muted-foreground">Open</span>}
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}
      {hb && hb.recent_movement.length > 0 && (
        <Section title="Recent movement">{hb.recent_movement.map((m) => `${fmtDate(m.date)} ${m.text}`).join(" · ")}</Section>
      )}
      {c.adherence && (
        <Section title="Treatment adherence">
          {c.adherence.visits.length} visits · last {fmtDate(c.adherence.visits.at(-1))}
          {c.adherence.current_gap_days != null && ` · ${c.adherence.current_gap_days}d since last visit`}
          {c.adherence.gaps.length > 0 && <p className="text-amber-700">Gaps: {c.adherence.gaps.map((g) => `${g.days}d (${fmtDate(String(g.from))}–${fmtDate(String(g.to))})`).join(", ")}</p>}
        </Section>
      )}
      {c.other_care && (
        <Section title="Other providers' care">
          <ul>{c.other_care.map((o) => <li key={o.provider_name}>{o.provider_name} · {fmtDate(o.first_visit)}–{fmtDate(o.last_visit)}</li>)}</ul>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">{title}</CardTitle></CardHeader>
      <CardContent className="text-sm">{children}</CardContent>
    </Card>
  );
}

export function movedAgo(iso?: string | null) {
  return iso ? `moved ${daysAgo(iso)}d ago` : "";
}
```

- [ ] **Step 5: Provider pages**

`frontend/app/(provider)/provider/cases/page.tsx`:
```tsx
"use client";
import Link from "next/link";
import { ErrorNote, Loading } from "@/components/common/states";
import { movedAgo } from "@/components/provider/ProviderCaseView";
import type { ProviderCaseSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function ProviderCases() {
  const { data, error, loading } = useApi<ProviderCaseSummary[]>("/api/provider/cases");
  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Your shared cases</h1>
      <ErrorNote error={error} />
      {loading ? <Loading /> : data?.length === 0 ? <p className="text-muted-foreground">No cases are shared with you right now.</p> : (
        <ul className="divide-y rounded border bg-background">
          {data?.map((c) => (
            <li key={c.grant_id}>
              <Link href={`/provider/cases/${c.grant_id}`} className="flex flex-wrap items-center gap-2 p-3 hover:bg-muted/50">
                <span className="font-medium">{c.patient_display}</span>
                {c.state && <span className="text-sm">● {c.state}</span>}
                <span className="text-sm text-muted-foreground">{movedAgo(c.last_movement_at)}</span>
                {c.open_requests > 0 && <span className="text-sm">{c.open_requests} request{c.open_requests > 1 ? "s" : ""} for you</span>}
                <span className="ml-auto text-sm underline">Open</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

`frontend/app/(provider)/provider/cases/[grant]/page.tsx`:
```tsx
"use client";
import { use } from "react";
import { toast } from "sonner";
import { ErrorNote, Loading } from "@/components/common/states";
import { ProviderCaseView } from "@/components/provider/ProviderCaseView";
import { api, apiUrl } from "@/lib/api";
import type { ProviderCase } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function ProviderCasePage({ params }: { params: Promise<{ grant: string }> }) {
  const grant = Number(use(params).grant);
  const { data, error, reload } = useApi<ProviderCase>(`/api/provider/cases/${grant}`);
  if (error) return <ErrorNote error={error.status === 404 ? { message: "This case is no longer shared with you." } : error} />;
  if (!data) return <Loading lines={8} />;
  return (
    <ProviderCaseView
      c={data}
      docHref={(id) => apiUrl(`/api/provider/cases/${grant}/documents/${encodeURIComponent(id)}`)}
      onMarkSent={async (id) => {
        await api(`/api/provider/requests/${encodeURIComponent(id)}/complete`, { method: "POST" });
        toast.success("Marked as sent — the firm can see it.");
        reload();
      }}
    />
  );
}
```

- [ ] **Step 6: Verify end-to-end (real backend, synthetic dev DB)**

Seed a throwaway DB that never touches `data/casepulse.db`:
```bash
DB_PATH=data/dev2-seed.db uv run python -c "
from backend.app.db import connect, migrate; from backend.tests.dev2_support import seed
migrate(); 
with connect() as db: seed(db)
print('seeded data/dev2-seed.db (password correct-horse-1)')"
mkdir -p data/files && printf '%%PDF-1.4 demo' > data/files/report.pdf
DB_PATH=data/dev2-seed.db make backend
```
As `attorney@firm.test`, create + release a grant to Provider A with curl, or wait for Task 12's UI. Then sign in as `provider-a@clinic.test` on a phone-width window (375 px): case list → open → only released sections render; "Mark sent" flips to ☑; "Open" serves the PDF. In devtools Network, the JSON has no keys for unshared sections. `npm run lint` (provider import rule) clean.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "feat(product): provider portal — case list, heartbeat page, mark sent, shared docs (F6/F7)"
```

---

### Task 12: Share Composer with live preview + audit timeline (PLAN 2.7, F5/F8)

**Files:**
- Create: `frontend/components/attorney/{ShareComposer.tsx,AuditTimeline.tsx}`
- Modify: `frontend/app/(attorney)/matters/[id]/share/page.tsx`

**Interfaces:**
- Consumes: `applyPolicy`, `Toggles`, `ProviderCaseView` (attorney may import provider components; not the reverse), `Chips`, `api`, `useApi`, types `Providers`, `Grant`, `ShareCandidates`, `ShareAudit`, `ProviderRequest`, `ProviderDraft`, `DraftFlag`, `ReleaseResult`
- Produces: `<ShareComposer matterId initialProvider?/>`, `<AuditTimeline audit/>`

- [ ] **Step 1: Audit timeline**

`frontend/components/attorney/AuditTimeline.tsx`:
```tsx
import { fmtDateTime } from "@/lib/format";
import type { ShareAudit } from "@/lib/types";

const LABEL: Record<string, string> = {
  released: "released", viewed: "viewed", document_opened: "opened", request_completed: "marked sent",
  request_dismissed: "dismissed request", revoked: "revoked", invite_sent: "invite sent", invite_accepted: "invite accepted",
};

export function AuditTimeline({ audit }: { audit: ShareAudit }) {
  const diff = new Map(audit.versions.map((v) => [v.policy.version, v]));
  return (
    <ol className="space-y-1 text-xs">
      {[...audit.events].reverse().map((e) => {
        const v = e.event === "released" && e.policy_version != null ? diff.get(e.policy_version) : undefined;
        return (
          <li key={e.id}>
            <span className="font-mono text-muted-foreground">{fmtDateTime(e.at)}</span>{" "}
            {e.event === "released" ? <b>v{e.policy_version} released</b> : LABEL[e.event] ?? e.event}
            {e.actor_email && <span className="text-muted-foreground"> · {e.actor_email}</span>}
            {typeof e.meta?.document_id === "string" && <span> · {String(e.meta.document_id)}</span>}
            {v && (v.added.length > 0 || v.removed.length > 0) && (
              <span className="text-muted-foreground"> ({v.added.map((a) => `+${a}`).concat(v.removed.map((r) => `−${r}`)).join(" ")})</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
```

- [ ] **Step 2: Composer**

`frontend/components/attorney/ShareComposer.tsx`:
```tsx
"use client";
import { Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Chips } from "@/components/citations/CitationChip";
import { ErrorNote, Loading } from "@/components/common/states";
import { ProviderCaseView } from "@/components/provider/ProviderCaseView";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { applyPolicy, type Toggles } from "@/lib/policy";
import type { DraftFlag, Grant, ProviderDraft, ProviderRequest, Providers, ReleaseResult, ShareAudit, ShareCandidates, ShareField } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { AuditTimeline } from "./AuditTimeline";

const FIELDS: [ShareField, string][] = [
  ["status", "Status & heartbeat"], ["coverage", "Coverage"], ["case_value", "Case value"], ["bills", "Their bills"],
  ["open_requests", "Open requests"], ["documents", "Documents"], ["adherence", "Treatment adherence"], ["other_care", "Other providers' care"],
];
const DEFAULT: Toggles = { fields: ["status", "open_requests"], document_ids: [], coverage_detail: "confirmed", status_note: "" };

export function ShareComposer({ matterId, initialProvider }: { matterId: number; initialProvider?: number }) {
  const providers = useApi<Providers>(`/api/matters/${matterId}/providers`);
  const grants = useApi<Grant[]>(`/api/matters/${matterId}/shares`);
  const [contactId, setContactId] = useState<number | null>(initialProvider ?? null);
  const provider = providers.data?.providers.find((p) => p.contact_id === contactId);
  const grant = grants.data?.find((g) => g.provider_contact_id === contactId && !g.revoked_at);
  const q = contactId ? `provider_contact_id=${contactId}` : null;
  const candidates = useApi<ShareCandidates>(q && `/api/matters/${matterId}/share-candidates?${q}`);
  const reqs = useApi<ProviderRequest[]>(q && `/api/matters/${matterId}/requests?${q}`);
  const audit = useApi<ShareAudit>(grant ? `/api/shares/${grant.id}/audit` : null);
  const [email, setEmail] = useState("");
  const [t, setT] = useState<Toggles>(DEFAULT);
  const [flags, setFlags] = useState<DraftFlag[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (!contactId && providers.data?.providers[0]) setContactId(providers.data.providers[0].contact_id); }, [providers.data, contactId]);
  useEffect(() => { setEmail(grant?.email ?? provider?.email ?? ""); }, [contactId, grant?.email, provider?.email]);
  useEffect(() => {   // start from the latest released policy, if any
    const last = audit.data?.versions.at(-1)?.policy;
    setT(last ? { fields: last.fields, document_ids: last.document_ids, coverage_detail: last.coverage_detail, status_note: last.status_note ?? "" } : DEFAULT);
    setFlags([]);
  }, [audit.data, contactId]);

  const preview = useMemo(() => (candidates.data ? applyPolicy(candidates.data, t) : null), [candidates.data, t]);
  const openFlags = flags.filter((f) => t.status_note.includes(f.text));   // a flag clears once its text is edited out
  const toggle = (f: ShareField, on: boolean) => setT((s) => ({ ...s, fields: on ? [...s.fields, f] : s.fields.filter((x) => x !== f) }));
  const nextVersion = (grant?.latest_version ?? 0) + 1;

  async function draft() {
    if (!contactId) return;
    const d = await api<ProviderDraft>(`/api/matters/${matterId}/provider-draft`, { json: { provider_contact_id: contactId, fields: t.fields } });
    setT((s) => ({ ...s, status_note: d.draft }));
    setFlags(d.flags);
  }

  async function release() {
    if (!contactId || !email.trim()) { toast.error("Provider email is required."); return; }
    setBusy(true);
    try {
      const g = grant ?? await api<Grant>("/api/shares", { json: { matter_id: matterId, provider_contact_id: contactId, email: email.trim() } });
      const r = await api<ReleaseResult>(`/api/shares/${g.id}/release`, {
        json: { fields: t.fields, document_ids: t.fields.includes("documents") ? t.document_ids : [], coverage_detail: t.coverage_detail, status_note: t.status_note || null },
      });
      toast.success(`Released v${r.policy.version}`);
      if (r.invite_url) toast(`Invite link (also in server console): ${r.invite_url}`, { duration: 20000 });
      grants.reload(); audit.reload();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : String(e));
    } finally { setBusy(false); }
  }

  async function revoke() {
    if (!grant || !confirm(`Revoke ${grant.provider_name ?? "this provider"}'s access? They lose access immediately.`)) return;
    await api(`/api/shares/${grant.id}/revoke`, { method: "POST" });
    toast.success("Access revoked");
    grants.reload();
  }

  async function dismiss(id: string) {
    await api(`/api/requests/${encodeURIComponent(id)}/dismiss`, { method: "POST" });
    reqs.reload(); candidates.reload(); audit.reload();
  }

  return (
    <div className="grid grid-cols-[360px_1fr] gap-4 p-4">
      <div className="space-y-4">
        <Card><CardContent className="space-y-2 pt-4 text-sm">
          <Label>Share with</Label>
          <select className="w-full rounded border bg-background p-2" value={contactId ?? ""} onChange={(e) => setContactId(Number(e.target.value))}>
            {providers.data?.providers.map((p) => <option key={p.contact_id} value={p.contact_id}>{p.name}</option>)}
          </select>
          <Input type="email" placeholder="provider@clinic.com" value={email} disabled={!!grant} onChange={(e) => setEmail(e.target.value)} />
          <p className="text-xs text-muted-foreground">{grant?.latest_version ? `current: v${grant.latest_version} (${fmtDate(grant.released_at)})` : "not shared yet"}</p>
        </CardContent></Card>

        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-sm">Fields</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {FIELDS.map(([f, label]) => (
              <div key={f}>
                <label className="flex items-center gap-2"><Checkbox checked={t.fields.includes(f)} onCheckedChange={(v) => toggle(f, v === true)} />{label}</label>
                {f === "coverage" && t.fields.includes("coverage") && (
                  <RadioGroup className="ml-6 mt-1" value={t.coverage_detail} onValueChange={(v) => setT((s) => ({ ...s, coverage_detail: v as Toggles["coverage_detail"] }))}>
                    <label className="flex items-center gap-2"><RadioGroupItem value="confirmed" />Confirmed only</label>
                    <label className="flex items-center gap-2"><RadioGroupItem value="limits" />Carrier + limits</label>
                  </RadioGroup>
                )}
                {f === "documents" && t.fields.includes("documents") && (
                  <div className="ml-6 mt-1 space-y-1">
                    {candidates.data?.available_documents.map((d) => (
                      <label key={d.id} className="flex items-center gap-2 text-xs">
                        <Checkbox checked={t.document_ids.includes(d.id)} onCheckedChange={(v) => setT((s) => ({ ...s, document_ids: v === true ? [...s.document_ids, d.id] : s.document_ids.filter((x) => x !== d.id) }))} />
                        {d.title}{d.page_count && ` (${d.page_count} pp)`}
                      </label>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center pb-1">
            <CardTitle className="text-sm">Status note</CardTitle>
            <Button size="sm" variant="outline" className="ml-auto" onClick={draft}><Sparkles className="mr-1 h-3 w-3" />Draft with AI</Button>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Textarea rows={4} value={t.status_note} onChange={(e) => setT((s) => ({ ...s, status_note: e.target.value }))} />
            {openFlags.length === 0
              ? <p className="text-xs text-emerald-700">✔ 0 confidential flags</p>
              : <ul className="text-xs text-destructive">{openFlags.map((f, i) => <li key={i}>⚠ “{f.text}” — {f.reason}</li>)}</ul>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-sm">Open requests (attorney view)</CardTitle></CardHeader>
          <CardContent className="space-y-1 text-xs">
            {reqs.data?.length === 0 && <p className="text-muted-foreground">None for this provider.</p>}
            {reqs.data?.map((r) => (
              <div key={r.id} className="flex items-start gap-2">
                <span className={r.state !== "open" ? "text-muted-foreground line-through" : ""}>{r.description}<Chips citations={r.citations} /></span>
                <span className="ml-auto text-muted-foreground">{r.state}</span>
                {r.state === "open" && <Button size="sm" variant="ghost" className="h-6 px-2" onClick={() => dismiss(r.id)}>Dismiss</Button>}
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="flex gap-2">
          {grant && <Button variant="outline" onClick={revoke}>Revoke</Button>}
          <Button className="ml-auto" disabled={busy || !contactId || openFlags.length > 0} onClick={release}>Release v{nextVersion} &amp; notify ▸</Button>
        </div>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-sm">Preview: exactly what {provider?.name ?? "the provider"} will see</CardTitle></CardHeader>
          <CardContent className="rounded bg-muted/30 p-4">
            <ErrorNote error={candidates.error} />
            {preview ? <ProviderCaseView c={preview} preview /> : contactId ? <Loading lines={6} /> : <p className="text-muted-foreground">Pick a provider.</p>}
          </CardContent>
        </Card>
        {audit.data && (
          <Card>
            <CardHeader className="pb-1"><CardTitle className="text-sm">History / audit</CardTitle></CardHeader>
            <CardContent><AuditTimeline audit={audit.data} /></CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
```

`frontend/app/(attorney)/matters/[id]/share/page.tsx`:
```tsx
"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, use } from "react";
import { ShareComposer } from "@/components/attorney/ShareComposer";

function Inner({ matterId }: { matterId: number }) {
  const p = useSearchParams().get("provider");
  return <ShareComposer matterId={matterId} initialProvider={p ? Number(p) : undefined} />;
}

export default function SharePage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  return <Suspense><Inner matterId={matterId} /></Suspense>;
}
```

- [ ] **Step 3: Verify the F5 acceptance loop (seeded dev DB from Task 11)**

1. As attorney, open `/matters/1001/share?provider=600`. Toggle each field → the preview re-renders instantly (Network tab shows no requests while toggling). Coverage radio switches between "✔ Coverage confirmed" and carrier + limits. Pick "Imaging report".
2. "Draft with AI" (stub draft until the checkpoint) → flags list; release stays disabled until the flagged text is edited out.
3. "Release v1 & notify" → toast; history shows `v1 released (+status …)`.
4. Incognito as Provider A → `/provider/cases/<grant>` matches the preview section for section. Open the doc. Back in the attorney window, reload → history shows `viewed` and `opened document:10`.
5. Toggle bills on → "Release v2" → provider reload shows v2 with bills.
6. Dismiss a request → it's struck through; the provider reload no longer lists it.
7. Revoke → provider reload shows "This case is no longer shared with you."

Run `npm run lint && npm test && npm run build`.

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(product): Share Composer with instant preview, AI note + flags, release/revoke, audit timeline (F5/F8)"
git push
```

---

### Task 13: AI cost tab + firm costs page (PLAN 2.9, F10)

**Files:**
- Create: `frontend/components/attorney/AiCostTab.tsx`
- Modify: `frontend/app/(attorney)/matters/[id]/page.tsx` (cost tab), `frontend/app/(attorney)/costs/page.tsx`

**Interfaces:**
- Consumes: `useApi`, `usd`, `fmtDateTime`, types `AiCostReport`, `FirmCostReport`; Recharts
- Produces: `<AiCostTab matterId/>`

- [ ] **Step 1: Matter AI cost tab**

`frontend/components/attorney/AiCostTab.tsx`:
```tsx
"use client";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorNote, Loading } from "@/components/common/states";
import { Card, CardContent } from "@/components/ui/card";
import { fmtDateTime, usd } from "@/lib/format";
import type { AiCostReport } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const SHADES = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];
const tok = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n));

export function AiCostTab({ matterId }: { matterId: number }) {
  const { data: r, error } = useApi<AiCostReport>(`/api/ai-costs?matter_id=${matterId}`);
  if (error) return <ErrorNote error={error} />;
  if (!r) return <Loading lines={6} />;
  const row = [{ name: "cost", ...Object.fromEntries(r.by_purpose.map((p) => [p.key, p.usd])) }];
  return (
    <div className="space-y-3 text-sm">
      {r.budget_pct != null && r.budget_pct >= 80 && (
        <div className="rounded border border-amber-400 bg-amber-50 p-2 text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          AI spend is at {r.budget_pct.toFixed(0)}% of this matter&apos;s {usd(r.budget_usd ?? 0)} budget. Nothing is blocked.
        </div>
      )}
      <Card><CardContent className="space-y-2 pt-4">
        <p className="flex flex-wrap gap-x-6">
          <b>Total {usd(r.total_usd)}</b>
          <span>One-time digestion {usd(r.one_time_usd)}</span>
          <span>Ongoing {usd(r.ongoing_usd)} ({r.ask_count} Asks, ≈{usd(r.avg_ask_usd)} ea)</span>
          {r.budget_usd != null && <span className="text-muted-foreground">budget {usd(r.budget_usd)} · {r.budget_pct?.toFixed(0)}% used</span>}
        </p>
        <div className="h-14"><ResponsiveContainer>
          <BarChart data={row} layout="vertical" margin={{ left: 0, right: 0 }}>
            <XAxis type="number" hide /><YAxis type="category" dataKey="name" hide />
            <Tooltip formatter={(v: number, k: string) => [usd(v), k]} />
            {r.by_purpose.map((p, i) => <Bar key={p.key} dataKey={p.key} stackId="a" fill={SHADES[i % SHADES.length]} />)}
          </BarChart>
        </ResponsiveContainer></div>
        <p className="text-xs text-muted-foreground">{r.by_purpose.map((p) => `${p.key} ${usd(p.usd)}`).join(" · ")}</p>
        <p>Saved by cache: <b>{usd(r.cache_savings_usd)}</b></p>
      </CardContent></Card>
      <Card><CardContent className="pt-4">
        <table className="w-full text-xs">
          <thead className="text-left text-muted-foreground"><tr><th>Time</th><th>User</th><th>Purpose</th><th>Model</th><th>Tokens in / out</th><th className="text-right">$</th></tr></thead>
          <tbody>
            {r.runs.map((x, i) => (
              <tr key={i} className="border-t">
                <td>{fmtDateTime(x.at)}</td><td>{x.user ?? "system"}</td><td>{x.purpose}</td><td>{x.model}</td>
                <td>{tok(x.input_tokens)} / {tok(x.output_tokens)}</td>
                <td className="text-right font-mono">{x.cache_hit ? "cache hit $0.00" : usd(x.cost_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}
```

In `matters/[id]/page.tsx`, replace `{/* Task 13: AiCostTab */}` with `<AiCostTab matterId={matterId} />`.

- [ ] **Step 2: Firm costs page (cuttable)**

`frontend/app/(attorney)/costs/page.tsx`:
```tsx
"use client";
import Link from "next/link";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { ErrorNote, Loading } from "@/components/common/states";
import { usd } from "@/lib/format";
import type { FirmCostReport } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function FirmCosts() {
  const { data, error } = useApi<FirmCostReport>("/api/ai-costs/firm?days=30");
  return (
    <div className="mx-auto max-w-4xl space-y-4 p-6">
      <h1 className="text-xl font-semibold">AI cost · last 30 days {data && `· ${usd(data.total_usd)}`}</h1>
      <ErrorNote error={error} />
      {!data ? <Loading /> : (
        <>
          <div className="h-40"><ResponsiveContainer><LineChart data={data.series}>
            <XAxis dataKey="date" fontSize={10} /><Tooltip formatter={(v: number) => usd(v)} />
            <Line dataKey="usd" stroke="var(--primary)" dot={false} />
          </LineChart></ResponsiveContainer></div>
          <ul className="divide-y rounded border text-sm">
            {data.matters.map((m) => (
              <li key={m.matter_id} className="flex p-2">
                <Link className="underline" href={`/matters/${m.matter_id}`}>{m.display_number} {m.description}</Link>
                <span className="ml-auto font-mono">{usd(m.total_usd)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify**

The matter "AI cost" tab against the stub shows totals that match `fixtures/ai_costs.json` (`$2.31`, 46% → no banner). Temporarily edit the fixture's `budget_pct` to 85 locally, confirm the banner, then `git checkout fixtures/ai_costs.json` (Dev 1's file: never commit changes to it). `/costs` renders. `npm run lint && npm run build`.

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(product): matter AI cost tab + firm cost page (F10)"
```

---

### Task 14: Checkpoint switch to real data + freeze readiness

**Files:**
- Modify: whatever drift the checkpoint reveals, **only** in Dev 2-owned files (most likely `sharing/sources.py` and `frontend/lib/types.ts`)
- Modify: `tasks/todo.md` (Review section)

**Interfaces:**
- Consumes: Dev 1's real DB (`data/casepulse.db`) and real endpoints

- [ ] **Step 1: Checkpoint merge (12:45)**: run the Merge protocol block at the top. Then, on `integration`:

```bash
uv run pytest -q                    # all suites, both devs
make backend & sleep 3 && make smoke
cd frontend && npx openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.ts && npx tsc --noEmit
```
Any type error → fix the alias in `lib/types.ts` (on `raghu`). Any projection miss → compare Dev 1's actual rows with the interface doc:
```bash
sqlite3 data/casepulse.db "SELECT meta FROM records WHERE type='medical_bill' LIMIT 3; SELECT meta FROM records WHERE type='document' LIMIT 3; SELECT kind, COUNT(*) FROM facts GROUP BY kind;"
```
Adjust `sources.py` only, re-run `uv run pytest backend/tests/test_sharing.py`, and update the seed in `dev2_support.py` to the real shape.

- [ ] **Step 2: Walk PLAN §8 rows for Dev 2** on real data: F3 (click every date/$/injury), F5, Roles (incognito invite → set password), F6 (unshared keys absent in JSON), F7, F8, RBAC (`/api/records/1` → 403, `/api/matters/1/ask` → 403, another grant id → 404), Revoke (404 + `revoked` event). Fix in place.

- [ ] **Step 3: Freeze checks**

```bash
grep -rn "fixtures" backend/app/api/{auth_routes,shares,provider}.py backend/app/sharing frontend/app frontend/lib frontend/components || echo "Dev 2 clean"
grep -rni "sapini" frontend backend || echo "no case names"
uv run pytest backend/tests/test_rbac.py backend/tests/test_sharing.py -q
cd frontend && npm run lint && npm test && npm run build
```
All four clean or green. After Dev 1 has merged, delete `backend/app/stubs.py` and `fixtures/` if they're now unused (`grep -rn "stubs" backend/app`).

- [ ] **Step 4: Review section + final merge**

Append to this file:
```markdown
## Review (fill at freeze)
- Tests: <paste pytest + vitest summary>
- PLAN §8 rows passed: <list>
- Drift fixed at checkpoint: <what changed in sources.py / types.ts>
- Known gaps / cut: <e.g. Deep-Dive swimlanes (2.10) cut>
```
Then run the Freeze block from the Merge protocol (after Dev 1 merges `ash`).

```bash
git add -A && git commit -m "chore(product): freeze — real data verified, stubs removed" && git push
```

---

## Out of scope / cut first

- **2.10 Deep-Dive swimlanes + Gantt:** cut. The Deep-Dive tab shows the full ranked timeline (Task 6) as the stretch fallback.
- Email notify beyond invites, adherence/other-care polish, Verify selection: in the PLAN §7 cut order if behind.
