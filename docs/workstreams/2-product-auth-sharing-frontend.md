# Workstream 2 — Product: Auth, Sharing & Frontend
**Owner: Dev 2 · branch `feat/product` · master plan: [`docs/PLAN.md`](../PLAN.md). The master plan wins on any conflict.**

> **No pre-existing scaffold.** Everything is defined in this repo's docs: the full layout is in PLAN §5.1, and `spec_sheet_v1.md` is superseded by PLAN.md. Ignore its `problem_adapter/`, `/jobs`, `/results` and `/review` references and its "no chat" non-goal. The team decided RAG Ask is in scope.

---

## 0. Paste this into your Claude Code session to start

```
You are Dev 2 on a 2-person hackathon team (Swans "Law-Di-Gras" Applied AI Hackathon, deadline 4:00 PM today).
Read docs/PLAN.md fully, then docs/workstreams/2-product-auth-sharing-frontend.md (your brief). Follow the brief exactly.
docs/PLAN.md supersedes spec_sheet_v1.md: there is NO pre-existing scaffold (ignore problem_adapter/, /jobs, /results,
/review); the repo layout is defined in docs/PLAN.md §5.1 — create frontend/ exactly as laid out there.
You own: frontend/ (entire Next.js app), backend/app/sharing/, backend/app/api/{auth_routes,shares,provider}.py,
backend/tests/test_{rbac,sharing}.py. Never edit files outside your ownership; frozen shared files
(contracts.py, schema.sql, main.py, db.py, llm.py, auth.py) change only via a tiny commit to main announced to Dev 1.
Never call Clio, never write to Clio, never hardcode case data (no case/client names in code).
Step 1 now: create branch feat/product and scaffold frontend/ (task 2.1). Do NOT touch backend/ until
`git log origin/main` shows the commit "contract: phase-0 scaffold"; then rebase onto it and continue with 2.2.
Work task by task in the order listed; commit after each task with a clear message; push the branch often.
```

---

## 1. Your mission in one paragraph

Dev 1 builds the **case intelligence**: Clio sync, OCR, RAG, AI digests, and cited facts, all exposed as JSON endpoints. You build everything that has **users, sharing, or pixels**:
- the **two-role login** (attorney = admin, provider = scoped)
- the **share grant / versioned policy / provider projection** backend
- the **attorney dashboard** with its Ask panel
- the **Share Composer with live preview**
- the **provider portal**

The judges are trial attorneys and AI builders. They will click every date to see its source (F3), and they will try to see data a provider shouldn't (RBAC). Make both bulletproof.

## 2. Ownership and rules

| You own (write freely) | Read-only for you | Never |
|---|---|---|
| `frontend/**` | Dev 1's tables: `records`, `facts`, `briefs`, `digests`, `provider_requests`, `document_pages`, `matter_visits` | Call the Clio API (that's Dev 1's `ClioClient`) |
| `backend/app/sharing/**` | Dev 1's endpoints (consume via HTTP from the frontend) | Write to Dev 1's tables |
| `backend/app/api/auth_routes.py`, `shares.py`, `provider.py` | Frozen shared files (below) | Hardcode case names, client names, or moment lists |
| `backend/tests/test_rbac.py`, `test_sharing.py` | | Show a fact without a citation |
| Tables: `users`, `invites`, `share_grants`, `share_policies`, `share_events`, `request_states` | | Expose raw notes, emails or documents to the provider role |

- **Frozen shared files** (created in Phase 0 by Dev 1): `backend/app/contracts.py`, `backend/db/schema.sql`, `backend/app/main.py`, `backend/app/db.py`, `backend/app/llm.py`, `backend/app/auth.py`. If you need a change, make a **tiny separate commit on `main`**, push it, and tell Dev 1. You **do own the hardening of `auth.py`** (task 2.2). Coordinate that single change the same way.
- **Router auto-discovery.** Any module in `backend/app/api/` exposing `router` is auto-included, so never edit `main.py` to register routes. **Every route must declare `Depends(require_role(...))` or be explicitly marked public.** A startup check fails the app otherwise.
- **Stubs.** Phase 0 ships stub endpoints serving `fixtures/*.json`. Build the UI against them. When you implement one of *your* endpoints for real, delete its stub and its fixture. By the freeze, `grep -rn fixtures backend/app frontend/app` must return nothing.

## 3. Timeline and handoff signals

| Clock | You |
|---|---|
| now → Phase 0 pushed (~10:50) | 2.1 frontend scaffold (only `frontend/`) |
| ~10:50 | `git fetch && git rebase origin/main` → run backend stubs → `make types` → 2.2 onward |
| **12:45 Checkpoint** | Both branches merged into a throwaway `integration` branch, `make smoke test`. Get `data/casepulse.db` from Dev 1 (AirDrop) or run `make sync digest` yourself. Switch the UI from stubs to real data |
| **14:45 Freeze** | Stubs deleted, branch pushed. Dev 1 merges `feat/intelligence` → `main`, then you merge `feat/product` → `main` and run `make types` |
| 14:45–15:15 | The user runs the E2E checklist (PLAN §8). Fix in place |

Commit after every task and push the branch at least every 30 min.

## 4. Endpoints

### You implement (backend, Python/FastAPI, SQLite)
```
{public}   POST /api/auth/login            {email,password} → sets httpOnly JWT cookie, returns {user}
{public}   POST /api/auth/logout
{public}   GET  /api/auth/me               → {id,email,name,role,provider_contact_id} | 401
{public}   POST /api/auth/invite/{code}/accept  {password,name} → creates/attaches provider user, logs in
{attorney} GET  /api/matters/{id}/share-candidates?provider_contact_id=   → ShareCandidates (F5)
{attorney} POST /api/shares                {matter_id, provider_contact_id, email} → grant (no policy yet)
{attorney} POST /api/shares/{grant}/release {fields, document_ids, coverage_detail, status_note} → new SharePolicy version + event + invite
{attorney} POST /api/shares/{grant}/revoke
{attorney} GET  /api/matters/{id}/shares    → grants with latest version, last viewed
{attorney} GET  /api/shares/{grant}/audit   → ShareEvent[] + per-version field diffs (F8)
{attorney} POST /api/requests/{id}/dismiss  (F7)
{provider} GET  /api/provider/cases                      → ProviderCaseSummary[] (own active grants only)
{provider} GET  /api/provider/cases/{grant}              → ProviderCase (F6) — logs 'viewed'
{provider} GET  /api/provider/cases/{grant}/documents/{doc} → file stream, only if doc ∈ latest policy — logs 'document_opened'
{provider} POST /api/provider/requests/{id}/complete     (F7 "Mark sent")
```

### You consume (implemented by Dev 1, stubbed until the checkpoint)
```
GET  /api/matters · /api/matters/{id}/overview · /timeline · /deadlines · /costs · /providers
POST /api/matters/{id}/visits → {previous_visit_at}     GET /api/matters/{id}/changes?since= · /delta?since=
GET  /api/matters/{id}/brief → story, key_moments, injuries, worth, coverage, waiting_on, last_client_contact
GET  /api/records/{record_id} · /api/documents/{id}/pages/{n} · /api/documents/{id}/file
POST /api/matters/{id}/ask  (SSE: event "segment" {id,text,citations[]} … event "done" {followups[]})
POST /api/matters/{id}/locate {text} → {supported, citations[]}
GET  /api/matters/{id}/suggested-questions · POST /api/matters/{id}/provider-draft
POST /api/digest/{matter_id} · GET /api/matters/{id}/digest-runs · GET /api/ai-costs?matter_id=
GET  /auth/clio/login (attorney "Connect Clio" button) · POST /api/sync/{matter_id} · GET /api/sync/status
```

Types come from `contracts.py` via `make types` (FastAPI OpenAPI → `frontend/lib/api-types.ts`). Never hand-write API types.

## 5. Key shapes you'll render (summary; `contracts.py` is authoritative)

- `Citation {record_id, source_type, title, author, date, page?, char_start, char_end, excerpt}`
- `Cited<T> {value: T, citations: Citation[]}`. There is always ≥ 1 citation.
- `NotFound {not_found: true, label}`. Render it as **"not found in file"**, never a blank or a guess.
- `WorthEstimate {low, high, label:"Estimate", assumptions: Cited<string>[], cap_note?}`
- `Coverage {carrier, bi_per_person, bi_per_accident, um_uim, medpay}`. Each field is `Cited<…> | NotFound`.
- `ChangeItem {record_id, change: new|changed|removed, importance, why_it_matters, citations}`
- `KeyMoment {date, title, importance, rank_reason, citations}`
- `Answer segments {id, text, citations[]}`. An uncited segment has `citations: []`.
- `ProviderCase {grant_id, policy_version, patient_display, heartbeat{state, last_activity_at, last_movement{date,text}}, coverage?, case_value?, bills?, requests?, documents?, adherence?, other_care?}`. **Keys are absent when not shared.**

## 6. Tasks, in order

### 2.1 Frontend scaffold (start immediately, only in `frontend/`)
- Next.js 15 (App Router, TypeScript), Tailwind, shadcn/ui, Recharts, `openapi-typescript`, `lucide-react`.
- Follow the `frontend/` tree in PLAN §5.1 (components split into `citations/`, `attorney/`, `provider/`). Route groups:
  - `app/(auth)/login`, `app/(auth)/invite/[code]`
  - `app/(attorney)/matters`, `app/(attorney)/matters/[id]`, `app/(attorney)/matters/[id]/share`, `app/(attorney)/costs`
  - `app/(provider)/provider/cases`, `app/(provider)/provider/cases/[grant]`
- `lib/api.ts`: fetch wrapper with `credentials: "include"`, base URL `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`), and SSE helper.
- Design tokens: calm legal palette, dense but readable, light and dark modes. Desktop-first (1440 px); the provider pages must also work on a phone.
- **Done when:** `npm run dev` boots and the pages render placeholder layouts from PLAN §3.

### 2.2 Auth: two login levels
- **Backend (harden `auth.py`, one coordinated commit to `main`):**
  - argon2-cffi password hashing
  - PyJWT HS256 cookie `cp_session` (httpOnly, SameSite=Lax, 8 h), `{sub, role}`
  - `current_user` reloads the user from the DB on every request
  - `require_role("attorney"|"provider")`
  - `make seed-attorney` reads `ATTORNEY_EMAIL`/`ATTORNEY_PASSWORD`/`ATTORNEY_NAME` from `.env`
- **Invites:** `invites(code_hash sha256, email, grant_id, expires_at 7d, used_at)`. Accepting creates a `role=provider` user (or attaches to an existing one with that email) and logs them in.
- **Frontend:** a login page posting to `/api/auth/login`, redirecting by role (attorney → `/matters`, provider → `/provider/cases`), plus `/invite/[code]` (set name + password) and sign-out.
- **`middleware.ts`:** calls `/api/auth/me` (or decodes the role claim), blocks `/matters/**` and `/costs` for providers, and blocks `/provider/**` for attorneys. This is UX only; the backend enforces.
- **The provider route group must not import any attorney component** (keep them in separate folders; a lint rule or review check is enough).
- **Done when:** both roles land on the right home; a wrong role gets redirected.

### 2.3 Citations UI (F3, non-negotiable)
- `<CitationChip citation>`: a compact chip (`[n12]`, `[d4 p112]`). Hover or click opens a popover with the **excerpt** + type, title, author and date, plus an "Open source" button.
- `<SourceDrawer>`: right-side sheet.
  - Text records (`GET /api/records/{id}`): render the body, wrap `char_start..char_end` in `<mark>`, `scrollIntoView`.
  - Document pages (`GET /api/documents/{id}/pages/{n}`): page image (left) + OCR text (right) with the span marked.
  - Prev/next across all citations of the current fact. "Open in Clio ↗" if a URL is present.
- Generic `<Cited value=… />` renders a value with its chips. `NotFound` renders "not found in file" in muted text.
- **Done when:** every chip on the page opens the exact span.

### 2.4 Attorney matter page, Brief mode (PLAN §3b)
- **On mount:** `POST /visits`, then `GET /changes?since=previous_visit_at` and `GET /delta?since=…`.
- **Header:** client photo, name, age, DOI, stage bar, last client contact (⚠ if > 30 days), status pill "Synced · Digested · cache hit · $x (case $y)" (F9/F10).
- **F1 panel "Since your last visit":**
  - items ranked by importance, each with score, title, `why_it_matters` and chips
  - AI delta summary on top
  - **explicit empty state:** "Nothing has changed since your last visit (date). Last activity on the case: …"
  - **first-visit state:** "First time opening this matter, showing the last 14 days"
  - never cache "new" badges client-side
- **F4 tiles:**
  - **Case Worth**: "Estimate" label, `$low – $high`, assumptions list, each with chips, cap note.
  - **Coverage**: each field cited or "not found in file".
  - Plus Firm Spend (sparkline), SOL / Next deadline.
- **Deadlines board:** Overdue / Coming / Waiting on, each item cited.
- **Story so far:** cited bullets.
- **F2 Key Moments:** ≤ 10, each with score, date, title, `rank_reason` and chips; "Show all N" expands the ranked timeline.
- **Injuries panel** (simple SVG body map, cited) and **Providers & Liens** (bills, balance, lien, last visit/gap, share status "v2 shared · opened 2×" → audit).
- **Done when:** it renders fully from stubs, then from real data at the checkpoint.

### 2.5 Ask panel (RAG with highlight-to-source)
- Docked right panel: suggested-question chips (`GET /suggested-questions`), input, history.
- Streams `POST /ask` SSE. Render each `segment` as `<span data-seg={id}>` with superscript citation chips.
- **Highlight-to-source:**
  - On `mouseup`, read `window.getSelection()` and find all `[data-seg]` spans intersecting the range.
  - Show a floating popover listing the union of their citations. Clicking one opens the `SourceDrawer`.
  - If any intersecting segment has `citations: []`, show **"Verify selection"**. It calls `POST /locate {text}` and shows the returned citations, or "No supporting source found in the case file."
- **Done when:** highlighting any text in an answer reaches its source.

### 2.6 Sharing backend (F5–F8), in `backend/app/sharing/` + `api/shares.py` + `api/provider.py`
- **Tables** (in `schema.sql`, already created in Phase 0): `share_grants`, `share_policies` (versioned; `fields` JSON keys: `status, coverage, case_value, bills, open_requests, documents, adherence, other_care`), `share_events`, `request_states`, `invites`.
- **`share-candidates`.** Builds every section this provider *could* see, **already scoped to that provider**:
  - their own bills only
  - requests addressed to them (`provider_requests.provider_contact_id`)
  - the documents list
  - coverage (both "confirmed only" and "limits" variants)
  - case value
  - adherence
  - other providers' care

  It reads Dev 1's tables and facts read-only.
- **`ProviderProjection(policy, conn) -> ProviderCase`**: the **only** code path that produces provider-visible data. It's a whitelist: start from an empty dict and add a key only if the policy grants it.
  - **heartbeat (always included when `status` is granted):**
    - `state` from the most recent activity date across the matter's records: Active ≤ 30d, Quiet 31–90d, Dormant > 90d, Closed if the matter is closed
    - `last_movement` = the latest record whose digest is `confidential = 0` and in a provider-safe category, using `provider_safe_summary`; else "Case activity recorded"
  - `coverage`: `coverage_detail = confirmed` → `{confirmed: bool}`; `limits` → cited limits
  - `documents`: only `policy.document_ids`
  - `requests`: open ones, with `request_states` applied
- **Release** inserts `share_policies(version = prev + 1)`, writes `share_event('released')` and creates an invite if the grant has no `provider_user_id`. Send the invite via Resend if `RESEND_API_KEY` is set; otherwise **print the invite URL to the server console**.
- **Provider endpoints:**
  - Every query filters `grant.provider_user_id = current_user.id AND revoked_at IS NULL`. Otherwise return 404 (not 403), so grant IDs can't be probed.
  - Log `viewed` and `document_opened` events.
  - Documents are served by proxying Dev 1's stored file, after checking membership in the latest policy.
- **Request state:** provider "complete" / attorney "dismiss" → `request_states` + `share_event`. **Never Clio.**
- **Audit:** events with actor email + per-version field diff (fields added/removed between versions).
- **Tests (`backend/tests/test_rbac.py`, `test_sharing.py`):**
  - Provider → every attorney route = 403.
  - Provider A → provider B's grant = 404.
  - Revoked grant = 404.
  - Unshared field keys are absent from the JSON.
  - A doc not in the policy = 404.
  - Release → version+1 + event.
  - View/doc-open events are recorded in order.
- **Done when:** both test files are green.

### 2.7 Share Composer (F5) + audit (F8): `app/(attorney)/matters/[id]/share`
- Provider picker comes from the matter's providers (`/providers`), with the email prefilled from Clio contact data or typed.
- Load `share-candidates` once. Field toggles + coverage detail radio + document multi-select.
- **Live preview:** render the *provider page components* (from 2.8) with `applyPolicy(candidates, toggles)`. This is a pure client-side key filter, so it re-renders instantly with no network.
- Status note: "Draft with AI" → `POST /provider-draft`. Editable, shows confidentiality flags; Release is blocked while flags remain.
- "Release vN+1 & notify" → `/release`. History/audit timeline: versions, field diffs, views, doc opens (with actor + time). Revoke.
- **Done when:** toggles change the preview instantly, and release → the provider's reload shows the new version.

### 2.8 Provider app (F6, F7)
- `/provider/cases`: cards with patient display name, heartbeat state, "moved Nd ago", open request count.
- `/provider/cases/[grant]`: heartbeat (state + last movement date/text), stage bar, coverage, "What the firm needs from you" checklist with **Mark sent**, your bills, recently shared documents (open via the logged endpoint), recent movement feed, optional adherence and other-care sections.
- **Render only keys that exist.** No "redacted" placeholders.
- These components are reused by the composer preview (2.7), so keep them pure (props in, no fetching inside).
- **Done when:** a provider sees exactly the released fields.

### 2.9 AI cost UI (F10)
- Header pill, plus a matter "AI cost" tab from `GET /api/ai-costs?matter_id=`: totals, one-time vs ongoing, stacked bar by purpose, runs table (time, user, purpose, model, tokens, $), "saved by cache", and a budget banner at ≥ 80%.
- Firm `/costs` page: cost per matter + 30-day trend (**cuttable**).

### 2.10 Deep-Dive (stretch, cut first)
- Swimlane timeline by record type, a treatment Gantt per provider, filters (type, importance, date), and a virtualized full list.

## 7. Definition of done for your branch at the freeze

- [ ] `pytest backend/tests/test_rbac.py backend/tests/test_sharing.py` green
- [ ] Every Dev 2 stub and fixture deleted (`grep -rn fixtures backend/app frontend/app` → nothing)
- [ ] No case or client names in code (`grep -rni sapini frontend backend` → nothing)
- [ ] Both roles work end to end against real data; preview == provider view
- [ ] Every number, date and injury on the attorney page has a working chip
- [ ] Branch pushed; PLAN §8 rows F3–F8, Roles, RBAC and Revoke pass locally

## 8. Never do
- Call or write to Clio. Write to Dev 1's tables. Edit frozen files without the coordination step.
- Show a fact without a citation. Invent coverage or limits; use "not found in file".
- Show "redacted" placeholders to providers; omit the data instead.
- Give the provider role any access to Ask, records, notes, emails or unshared documents.
- Hardcode any case-specific string, moment list or provider name.
