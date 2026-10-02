# Plan — "Case Pulse": a cited case dashboard with RAG and two-role access, for PI firms and their medical providers
**Team of 2 devs · two parallel branches · final merge → end-to-end test**

> **Shared source of truth for both developers.** Dev 1's agent works from `docs/workstreams/1-case-intelligence.md`; Dev 2's agent works from `docs/workstreams/2-product-auth-sharing-frontend.md`. Both briefs defer to this file.

## ▶ Reconciliation with `spec_sheet_v1.md` (commit d62f5b9)
This plan adopts the spec sheet's F1–F9 **verbatim as acceptance criteria** (§1) and its access model. Three deliberate differences:

1. **RAG "Ask the case" is IN scope.** The spec lists chat as a non-goal; the team lead decided to add it as a *secondary* "dig into everything" layer. Every sentence is cited, with highlight-to-source. The dashboard stays the primary, question-free surface, and the 90-second demo still leads with F1 → F3 → F5 → F6.
2. **Provisioning = invite link → provider sets a password → provider login.** This is a real, separate provider account. It satisfies the spec's "access token/link" step, plus the team's two-login requirement. A demo role switcher is optional, never a substitute.
3. **"Existing scaffold" (`problem_adapter/`, `/jobs`, `/results`, `/review`) is not in this repo.** If it exists elsewhere, push it to `main` before Phase 0 and Phase 0 will wire into it. Otherwise this plan's layout (`backend/` FastAPI + `frontend/` Next.js) is the scaffold.

**Note on "activities feed":** in the Clio v4 API, `activities` are time and expense entries, not an audit log. F1's change feed is therefore built from sync-time diffs (§1 F1).

## ▶ Execution order

1. **Docs** (this commit): `docs/PLAN.md` + two self-contained workstream briefs.
2. **Phase 0 contract scaffold** (Dev 1, ≈ 30 min, pushed to `main` as `contract: phase-0 scaffold`):
   - `pyproject.toml` (uv, Py 3.12), `Makefile`, `.env.example`, `.gitignore`
   - `backend/db/schema.sql` (SQLite), `backend/app/{main.py, contracts.py, auth.py, llm.py, db.py}`
   - stub routers for **every** endpoint serving `fixtures/*.json`
   - `scripts/smoke.py`

   Meanwhile Dev 2 scaffolds `frontend/` (its own dir), so nobody waits.
3. **Parallel build:** Dev 1 on `feat/intelligence`, Dev 2 on `feat/product`. Checkpoint merge at 12:45, freeze + final merge at 14:45.

**Environment:**
- uv-managed **Python 3.12**, needed to load SQLite extensions (macOS system Python can't).
- Node 20.
- **SQLite (WAL) + sqlite-vec + FTS5** at `data/casepulse.db`, gitignored because it holds case data.
- Local embeddings: `BAAI/bge-base-en-v1.5` via fastembed, run on Dev 1's Mac.
- Dev 2 either runs `make sync` against the team Clio account or receives a copy of the `.db` at the checkpoint.

---

## Context

**Hackathon:** Swans Applied AI Hackathon (Law‑Di‑Gras, San Diego), **today, Oct 2 2026**. Hard deadline **4:00 PM**: repo committed and form in. Submit early, because earlier submissions present first.

**Problem:** Clio Manage already *captures* the case. Nobody has solved *digesting* it.

**Challenge, both halves required:**
1. Get firm members up to speed on a case.
2. Give lien-treating medical providers visibility into the case and a channel to communicate.

The slide also says: *"beyond an AI chat… a visual digestion"*.

**Our answer: one citation engine, two surfaces, two roles.**
- A **visual dashboard** for the 2-minute read. It needs no questions.
- A **RAG "Ask the case" panel** for the dig-into-everything read. The attorney can highlight any text in an answer and jump to its exact source span.
- **Attorney (admin) login** sees everything.
- **Provider login** sees only what an attorney released to that provider, and nothing more.

Every date, dollar figure, injury and claim carries ≥ 1 stored citation with an excerpt.

**Hard rules (slide 16):**
- Read **live** from our Clio account.
- **GET-only** calls to Clio, enforced in code.
- **No hardcoding.** Judges read the repo, and there is no "Sapini" string anywhere in code.
- Our own DB holds everything we write.
- We must report **models used and $ per case**. The app measures this.

**Two workstreams.** The boundary is "touches Clio or an LLM" vs "touches users, sharing or pixels":

| | **Dev 1: Case Intelligence** (`feat/intelligence`) | **Dev 2: Product** (teammate, `feat/product`) |
|---|---|---|
| Scope | Clio client + sync, documents + OCR, embeddings + RAG, digests, extraction, value model, brief, Ask/locate, attorney data endpoints, visits/changes, cost tracking | Auth + roles + invites, share grants/policies/projection, provider endpoints, request states, audit, **the entire Next.js frontend** (attorney + provider apps) |
| Writes tables | `records`, `document_pages`, `chunks*`, `digests`, `digest_runs`, `facts`, `briefs`, `provider_requests`, `qa_log`, `ai_runs`, `matter_visits`, `clio_tokens`, `sync_state` | `users`, `invites`, `share_grants`, `share_policies`, `share_events`, `request_states` |
| Reads the other's tables | `users` (via `auth.py`) | `records`, `facts`, `briefs`, `digests.provider_safe_summary`, `provider_requests` (read-only, for the projection) |

---

## 1. Must-ship features F1–F10: spec → implementation → acceptance

### F1 — "Changed since your last visit" digest (top of the attorney matter page)

**Implementation**
- **Per-user visits.** Table `matter_visits(user_id, matter_id, visited_at)`.
  - `POST /api/matters/{id}/visits` returns `{previous_visit_at}`.
  - A reload within 30 min reuses the same visit, so refreshing never wipes the delta.
- **Fresh data first.** Opening a matter triggers an incremental Clio sync (`updated_since`) before computing the diff.
- **Change tracking at sync time.** Each `records` row has `first_seen_at`, `last_changed_at` (set only when `content_hash` changes), and `deleted_at`.
- **The "activity feed".** Clio v4 has no general audit-log endpoint. The feed is the union of everything synced (notes, communications, tasks, calendar entries, documents, `activities` time/expense entries, bills, medical records/bills) plus stage/status changes detected by diffing our snapshots.
- **The diff.** `GET /changes?since=` returns new, changed and removed records, ranked by digest `importance`. Each has a one-line `why_it_matters` + citations. An AI delta summary sits on top, cached by the hash set.
- **Empty state is explicit:** *"Nothing has changed since your last visit (Sep 28, 10:14). Last activity on the case: Sep 20, note by J. Doe."*
- **First visit:** *"First time opening this matter, showing the last 14 days."*
- **No stale badges.** "New" badges are computed per request from the baseline, never stored.

**Owners:** Dev 1 (visits, tracking, `/changes`, `/delta`), Dev 2 (panel).

**Accept:** edit a note in the Clio UI and reopen → only that note shows, with why + chip. Reopen again → "Nothing has changed…".

### F2 — Key moments ("the 10 from 300")

**Implementation**
- **Candidates.** Every record gets a Haiku digest: `importance` 1–10, `importance_reason`, category.
- **Selection.** Opus picks and orders ≤ 10 moments from candidates with importance ≥ 6. Each carries `rank_reason` + ≥ 1 citation.
- **No hardcoded moments.** The prompt holds a generic PI-importance rubric only. There is no moment list in code.
- **Display.** Score + reason + chips; "Show all N" expands the rest, ranked.

**Owners:** Dev 1 (digest, selection), Dev 2 (UI).

**Accept:** every moment has a reason and an openable citation; grep finds no moment literals.

### F3 — Click-to-source citations (non-negotiable)

**Implementation**
- **One contract type:** `Citation {record_id, source_type, title, author, date, page?, char_start, char_end, excerpt}`.
- **The contract enforces it.** `Cited[T]`'s Pydantic validator requires ≥ 1 citation with a non-empty excerpt. An API cannot emit an uncited fact.
- **Three citation sources:**
  - **AI facts:** structured-output `evidence {chunk_id, quote}`. The quote is fuzzy-matched in the chunk to get offsets. Unverified facts are **dropped**.
  - **Ask/RAG:** native `search_result` citations, mapped deterministically (§4).
  - **Structured Clio facts:** a deterministic citation to the record, with the excerpt rendered from fields, e.g. "Medical bill · ABC Ortho · $22,140 · 05/02/24".
- **UI:** chip → popover (excerpt + type/title/author/date) → Source Drawer (note/email with the span highlighted, or the PDF page image + OCR text with the span highlighted) → "Open in Clio ↗".

**Owners:** Dev 1 (contract, verification, structured citations, source endpoints), Dev 2 (chip, popover, drawer).

**Accept:** every date, $ and injury resolves to an excerpt. A contract test proves an uncited fact fails validation.

### F4 — Case worth + coverage KPIs

**Worth is always a range, labeled "Estimate", with three cited assumptions:**

| Assumption | Where it comes from |
|---|---|
| Bills total | Σ medical bills, each cited, plus other special damages |
| Injury severity found | Tier: soft-tissue / objective / surgical, cited |
| Policy limits found | Cited coverage facts, or "not found in file" |

- **The range math is deterministic code.**
  - `specials × multiplier band(tier)` from `backend/app/ai/value_model.yaml`, a generic, documented PI heuristic.
  - When limits are found, the tile adds "recovery may be capped by available coverage of $X".
  - **The LLM only extracts cited inputs; it never outputs the number.**
- **Coverage tile:** carrier, BI per-person/per-accident, UM/UIM, MedPay, each cited or **"not found in file"**, never inferred.

**Owners:** Dev 1 (extraction, value model, totals), Dev 2 (tiles + "why" expander).

**Accept:** the range shows 3 cited assumptions; a missing field says "not found in file".

### F5 — Share composer with live provider preview

**Implementation**
- **Steps:** pick a provider (from the matter's Clio contacts) → toggle **status, coverage, case value, bills, open requests, documents** (+ optional adherence, other providers' care) → pick specific documents → edit the AI status note (confidentiality-checked) → **live preview as that provider**.
- **Instant preview.** `GET /share-candidates?provider_contact_id=` returns every section the provider *could* see, already scoped to them. The preview is a pure client-side filter by the toggles: instant, no LLM, no network.
- **Release.** `POST /api/shares/{grant}/release` writes a new **`share_policies` version** + a `share_event('released')`, and invites the provider if they have no account yet.
- **Provider view is never stale.** It's computed **per request** from the latest released policy applied to live data, so it reflects the change on next load.
- **Truthful preview.** The preview and the real provider page use the **same React components** with the same `ProviderCase` shape.

**Owners:** Dev 2 (grants, policies, candidates, release, projection, composer UI), Dev 1 (`POST /provider-draft` + classifier).

**Accept:** toggles re-render instantly; release → v+1 in history → the provider's reload shows exactly v+1.

### F6 — Provider case heartbeat

**What's on it:**
- **Alive**, derived from recent activity:

  | State | Rule |
  |---|---|
  | Active | ≤ 30d |
  | Quiet | 31–90d |
  | Dormant | > 90d |
  | Closed | matter closed |

- **Last movement:** date + plain-language text drawn only from **provider-safe** events (stage/status change, records/bills received, appointments, documents shared), using `digests.provider_safe_summary`. If the latest event is confidential, it shows "Case activity recorded".
- Coverage (if shared), "what the firm needs from you" (F7), recently shared documents.
- **Unshared fields are absent** from the JSON and the DOM, never redacted.

**Owners:** Dev 2 (projection + screen), Dev 1 (`provider_safe_summary`, activity dates).

**Accept:** unshare coverage → the key is absent from the JSON; "alive" follows the activity dates.

### F7 — "What the firm needs from me" (provider requests)

**Implementation**
- **Extraction (Dev 1).** Sources: tasks mentioning the provider or records/bills/authorizations, communications to the provider's email, open `medical_records_details`. Each becomes `provider_requests(id, matter_id, provider_contact_id, kind records|bills|authorization|other, description, requested_at, citations)`.
- **State is app-local (Dev 2).** `request_states(request_id, state open|completed|dismissed, by_user_id, at)`. It never touches Clio.
  - The provider can "Mark sent"; the attorney can dismiss.
  - Both actions write a `share_event`.
- **Citations by audience.** The attorney sees the full citation. The provider sees description + date + channel, and sees the excerpt only if the source was a message addressed to them.

**Accept:** every request is cited (attorney view); "Mark sent" persists; the GET-only test is green.

### F8 — Share audit trail

**Implementation**
- **Event log.** `share_events(id, grant_id, policy_version, event released|viewed|document_opened|request_completed|request_dismissed|revoked, actor_user_id, actor_email, at, meta)`. It's append-only.
- Provider documents are served only via `/api/provider/cases/{grant}/documents/{doc}`, which checks the document is in the latest policy and logs `document_opened`.
- **Audit view.** Per provider: a release timeline (diff vs the previous version) plus every open.

**Owners:** Dev 2.

**Accept:** release → view → open doc produces 3 ordered events with actor and time.

### F9 — Digest caching + cost-per-case instrumentation

**Implementation**
- **Digest rows** store `content_hash, model, input_tokens, output_tokens, cost_usd`.
- **Run log.** `digest_runs(id, matter_id, trigger, records_seen, records_changed, llm_calls, input_tokens, output_tokens, cost_usd, cache_hit)`.
- **Cache keys.** Each stage (OCR, chunk/embed, digest, extract, brief) is keyed by its input hash.
- **Demo.** `make cache-demo`: the second run prints `0 LLM calls · $0.00 · cache hit`.
- **README** reports the measured one-time Sapini cost plus the per-Ask cost.

**Owners:** Dev 1 (pipeline, logging), Dev 2 (status pill).

**Accept:** the second run makes 0 LLM calls, and the README number matches `digest_runs`.

### F10 — LLM cost monitoring for attorneys (small, attorney-only)

**Data:** every Claude call goes through `llm.py`, which writes `ai_runs(matter_id, user_id, purpose ocr|digest|extract|brief|ask|locate|draft, model, input_tokens, output_tokens, cache_read_tokens, cost_usd, at)`.
- Prices: Opus 5.5 $4/$20, Haiku 4.5 $1/$5 per MTok, cache reads discounted.
- Local embedding runs are logged at $0, with their duration.

**Endpoint:** `GET /api/ai-costs?matter_id=&from=&to=` returns:
- totals
- breakdown by purpose and by model
- one-time vs ongoing
- per-Ask cost
- cache-hit savings
- a daily series
- budget % (`.env` default + per-matter override)

**UI:**
- cost pill in the matter header
- matter "AI cost" tab: stacked bar, runs table, "saved by cache", and a budget banner at 80% (nothing is blocked)
- firm page `/costs` (cuttable)

**Owners:** Dev 1 (endpoint), Dev 2 (UI).

**Accept:** total = `SUM(ai_runs.cost_usd)`; each Ask is its own row; a cache-hit run adds $0.00.

```
┌ AI COST — this matter ──────────────────────────── budget $5.00 · 46% used ┐
│ Total $2.31   One-time digestion $1.96   Ongoing $0.35 (4 Asks, ≈$0.09 ea)  │
│ ████████ OCR $0.82 ▓▓▓▓ digest $0.61 ░░░ extract/brief $0.53 ▒ ask $0.35    │
│ Saved by cache: $5.70 (3 re-opens, 1 no-change sync)                        │
│ 10:42 J.Doe  ask      opus-5-5   18.2k in / 0.7k out   $0.087               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Remaining quote coverage (beyond F1–F10)

| Quote | Feature | Owner |
|---|---|---|
| Up to speed + recent | **90-sec Brief**: cited story bullets + recent strip | 1 · 2 |
| 2 min vs dig into everything | Brief ⇄ Deep-Dive + **Ask the case (RAG)** with highlight-to-source | 1 · 2 |
| Client's picture | Header photo: contact avatar → else a person-photo image doc (vision check) | 1 · 2 |
| Injuries in a 200-page scan | OCR every scanned page → cited Injuries panel (page-level) + body map | 1 · 2 |
| Last talked to the client | Last Client Contact KPI (comms with the client + notes tagged client-contact), cited | 1 · 2 |
| Overdue / coming / waiting on | Deadlines board, three columns (tasks, calendar, SOL, AI "waiting-on"), cited | 1 · 2 |
| Firm spend | Costs tile + chart (`activities` ExpenseEntry), cited | 1 · 2 |
| Secure sharing / two logins | Role-based auth (§4); provider accounts only via an attorney's release | 2 |
| P: Tell me when it moves | Provider "Recent movement" feed from the live projection + optional email | 2 |
| P: One eye closed | Optional "other providers' care" toggle | 2 |
| P: Is my patient showing up | Optional "treatment adherence" toggle: visit timeline + gap detection (visit data from 1) | 1 · 2 |

---

## 3. Wireframes

### 3a. Login (one page, role-based redirect)
```
┌──────────── ◉ Case Pulse ────────────┐
│ Email    [                         ] │  attorney → /matters          (everything)
│ Password [                         ] │  provider → /provider/cases   (released scope only)
│ [ Sign in ]   First time? Use the    │  /invite/{code} → set password
│ invite link from your email.         │
└──────────────────────────────────────┘
```

### 3b. Attorney matter page: Brief mode + Ask panel
```
┌──────────────────────────────────────────────────────────────────┬──────────────────────────────┐
│ ◉ Case Pulse [Matter ▾]  [Brief|Deep-Dive] [Share▸]  Attorney ▾  │ 💬 ASK THE CASE              │
│ Synced 10:41 · Digested 10:42 · cache hit · $0.00 (case $2.31)   │ Suggested: [Primary injuries]│
├──────────────────────────────────────────────────────────────────┤ [Coverage?] [Blocking demand]│
│ ┌────┐ CLIENT NAME · 34y · DOI 03/14/24 [n3] · Stage Treatment   │ ──────────────────────────── │
│ │FOTO│ Last client contact: 23d ago · call · paralegal [c41] ⚠   │ Q: Primary injuries?         │
│ └────┘                                                           │ A: MRI confirms an ▓L4-L5    │
├──────────────────────────────────────────────────────────────────┤ disc herniation▓¹ with       │
│ 🆕 SINCE YOUR LAST VISIT (Sep 28 10:14) — 3 changes, by importance│ radiculopathy¹; cervical     │
│ 9 ▸ Adjuster requested IME [e91]  why: affects demand timing     │ strain treated with PT².     │
│ 7 ▸ Ortho records received [d17]  why: completes treatment file  │  ┌ selection → Sources ──┐   │
│ (or: "Nothing has changed since your last visit…")               │  │ ¹ MRI Report p.112 ▸  │   │
├────────────────────────────┬─────────────────────────────────────┤  │ [Verify selection]    │   │
│ CASE WORTH — ESTIMATE      │ COVERAGE                            │  └──────────────────────┘    │
│ $150k – $250k              │ Carrier: Acme Mutual [d9 p2]        │                              │
│ • Bills $84.2k [12 bills▸] │ BI: $100k / $300k [d9 p2]           │                              │
│ • Severity: objective [d4] │ UM/UIM: not found in file           │                              │
│ • Limits $100k may cap[d9] │ MedPay: $5k [e12]                   │                              │
├──────────────┬─────────────┴──────┬──────────────────────────────┤                              │
│ FIRM SPEND   │ ⏰ OVERDUE·COMING·WAITING ON │ 📝 STORY SO FAR (cited)│                              │
├──────────────┴────────────────────┴──────────────────────────────┤                              │
│ ⭐ KEY MOMENTS — 10 of 312 (score · reason · source) [show all ▸]│                              │
│ 10 03/14/24 Accident & ER visit — defines liability+DOI [d2 p1]  │ [ask anything…          ⏎]   │
├──────────────────────────────┬───────────────────────────────────┤                              │
│ 🩺 INJURIES (cited, body map) │ 👩‍⚕️ PROVIDERS · LIENS · SHARES    │                              │
│                              │ ABC Ortho $22.1k LIEN · v2 shared │                              │
│                              │ 10/01 · opened 2× [audit ▸]       │                              │
└──────────────────────────────┴───────────────────────────────────┴──────────────────────────────┘
```

### 3c. Source Drawer
```
┌ 📄 MRI Report – Lumbar.pdf · page 112/214 · uploaded 04/03/24 · by Records Dept ─┐
│ [ page image ]          │ … impression: ▓L4-L5 posterior disc herniation with   │
│                         │ left neural foraminal narrowing▓ …  (scrolled to span) │
│ ◂ prev cite  next cite ▸│ [Open in Clio ↗]                                       │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 3d. Share Composer (attorney): live preview
```
┌ Share with [ABC Orthopedics ▾] · records@abcortho.com · current: v2 (10/01) ─────────────┐
│ FIELDS                        │ PREVIEW — exactly what ABC Orthopedics will see           │
│ ☑ Status & heartbeat          │ ┌───────────────────────────────────────────────────────┐ │
│ ☑ Coverage (•confirmed ○limits)│ │ (live render of 3f; toggling updates instantly)      │ │
│ ☐ Case value                  │ └───────────────────────────────────────────────────────┘ │
│ ☑ Your bills                  │ HISTORY / AUDIT                                           │
│ ☑ Open requests (2)           │ v2 released 10/01 09:02 by J.Doe (+coverage)              │
│ ☑ Documents: ☑ MRI p.1-3 ☐ ER │ viewed 10/01 09:14 dr.lee@… · opened "MRI" 09:15          │
│ ☐ Treatment adherence  ☐ Other providers' care                                            │
│ STATUS NOTE (AI draft ✎) ✔ 0 confidential flags        [Revoke] [Release v3 & notify ▸]  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3e. Provider home `/provider/cases`
```
┌ ABC Orthopedics · Dr. Lee ─────────────────────────────────────────── [Sign out] ┐
│ M. S. · ● Active · moved 3d ago · 2 requests for you                     [Open]  │
│ J. R. · ● Closed 08/12                                                   [Open]  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 3f. Provider heartbeat `/provider/cases/{grant}`: only released fields exist
```
┌ Patient M. S. · shared by Firm X · policy v2 ────────────────────────────────────┐
│ ● ACTIVE  ·  Last movement 09/29: "Case moved to Demand stage"                    │
│ COVERAGE: ✔ Coverage confirmed                                                    │
│ WHAT THE FIRM NEEDS FROM YOU                                                      │
│ ☐ Records 06/01–09/01 · requested 09/20 by email   [Mark sent]                    │
│ ☐ Updated itemized bill · requested 09/28          [Mark sent]                    │
│ YOUR BILLS: $22,140 billed · $18,000 balance · lien on file                       │
│ RECENTLY SHARED DOCUMENTS: MRI Report (p.1-3) · shared 10/01   [Open]             │
│ RECENT MOVEMENT: 09/29 Demand stage · 09/12 ER records received                   │
└───────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Architecture

```
                    ┌──────── SQLite (WAL) data/casepulse.db + sqlite-vec + FTS5 ───────┐
 Clio (GET only) ─▶ │ [1] records document_pages chunks chunk_vectors chunks_fts digests  │
 OAuth · 45 rpm     │     digest_runs facts briefs provider_requests qa_log ai_runs       │
                    │     matter_visits clio_tokens sync_state                            │
                    │ [2] users invites share_grants share_policies share_events          │
                    │     request_states                                                  │
                    └───────────▲────────────────────────────────────────▲───────────────┘
   Dev 1 FastAPI routers: sync, matters, records,         Dev 2 FastAPI routers: auth_routes,
   changes, brief, ask, digest, ai-costs                  shares, provider (ProviderProjection)
                                   ▲                                ▲
                                   └──── Dev 2 Next.js 15 (attorney app + provider app) ────┘
```

- **Backend:** Python 3.12 (uv), FastAPI, stdlib `sqlite3` + `sqlite-vec` (`vec0 float[768]`) + FTS5, PyMuPDF, `anthropic` SDK, `fastembed`, argon2-cffi, PyJWT.
- **SQLite dialect:**
  - JSON stored as TEXT (`json_extract`)
  - enums as CHECK constraints
  - ISO-8601 TEXT timestamps
  - single uvicorn process, WAL
- **Frontend:** Next.js 15 (TS, App Router), Tailwind, shadcn/ui, Recharts, `openapi-typescript`.
- **Models:**

  | Model | Used for | Notes |
  |---|---|---|
  | `claude-opus-5-5` | Ask, extraction, key moments, brief | effort `medium` for Ask, `low` for extraction |
  | `claude-haiku-4-5` | OCR (vision), per-record digests, entailment | — |
  | `BAAI/bge-base-en-v1.5` | Embeddings | Local, via fastembed |

- **Rough cost:** ≈ $2–3 one-time per case, cents per refresh, ≈ $0.10 per Ask. The measured figure goes in the README.

### RAG + citations (Dev 1)
1. **Chunking.** Records and OCR'd pages are cut into ~400-token chunks, keeping sentence **units** with char offsets.
2. **Hybrid retrieval.** sqlite-vec KNN top‑30 and FTS5 bm25 top‑30 are fused with RRF, then filtered by matter, type and date. The top‑12 go to Claude.
3. **Native citations.** Chunks are sent as **`search_result` blocks**:
   - `source = "{record_id}#p{page}"`
   - one text block per sentence unit, with `citations.enabled`
   - The returned `search_result_location` (`search_result_index`, `start/end_block_index`) maps deterministically to `(record_id, page, char_start, char_end, excerpt)`.
4. **Agentic Ask.** Opus 5.5 streams over SSE with two tools:
   - `search_case(query, types?, date_from?, date_to?)`
   - `get_case_metrics(kind)`, returning cited totals
5. **Answer contract.** `Answer {segments:[{id,text,citations[]}], followups[]}`.
6. **Highlight-to-source (Dev 2 UI).**
   - Selection → intersecting segments → sources popover → drawer.
   - For an uncited selection, "Verify selection" calls `/locate` (retrieval + Haiku entailment), which returns sources or "no supporting source found".
7. **Dashboard facts.** Structured outputs, which can't be combined with citations, return `evidence[{chunk_id, quote}]`. Each quote is verified, and unverified facts are dropped.
8. **Guardrails.** The model answers only from sources and says when something isn't found. **The provider role has no Ask and no raw-record access.**

### Auth and two roles (Dev 2; working minimal version in Phase 0)
| | Attorney (admin) | Provider |
|---|---|---|
| Sees | All matters, the full dashboard, Ask, all sources, audit, AI cost | Only matters with an active grant, only fields in the latest released policy |
| Does | Connect Clio, sync, share/release/revoke, dismiss requests | View heartbeat, open shared docs, "Mark sent" |

- **Tables:**
  - `users(id, email, password_hash, name, role, provider_contact_id)`
  - `invites(code_hash, email, grant_id, expires_at, used_at)`
  - `share_grants(id, matter_id, provider_contact_id, provider_user_id, revoked_at)`
  - `share_policies(grant_id, version, fields JSON, document_ids JSON, coverage_detail, status_note, released_by, released_at)`
- **Sessions.** JWT in an httpOnly, SameSite=Lax cookie. The user is re-loaded per request, so revocation is immediate.
- **Accounts.** `make seed-attorney` creates attorneys from `.env`. Provider accounts are created **only** via an attorney's release (invite → set password).
- **Enforcement (backend is the authority):**
  1. Every router declares `require_role(...)`, and a startup check rejects any route without one (deny-by-default).
  2. Provider endpoints return **only** `ProviderProjection(latest_policy, live data)`, a whitelist builder.
  3. Row ownership on every provider query (`grant.provider_user_id = me AND revoked_at IS NULL`), plus document IDs checked against the policy.
- **Next.js `middleware.ts`** routes by role (UX only). The provider bundle doesn't import attorney components.

---

## 5. Phase 0 (Dev 1, pushed to `main`) + endpoint contract

| Deliverable | File(s) | Later owner |
|---|---|---|
| `pyproject.toml` (uv, Py 3.12), `.env.example`, `Makefile` (`setup migrate seed-attorney backend frontend sync digest cache-demo smoke types test`), `.gitignore` | root | shared |
| SQLite schema (all tables, owner comments) + `db.py` (WAL, sqlite-vec load, migrations) | `backend/db/schema.sql`, `backend/app/db.py` | shared (frozen) |
| `contracts.py`: `Citation`, `Cited[T]` (≥ 1 citation, excerpt required), `NotFound`, `ChangeItem`, `KeyMoment`, `WorthEstimate`, `Coverage`, `Overview`, `TimelineItem`, `Deadlines`, `Costs`, `SourceRecord`, `Brief`, `Answer`, `ShareCandidates`, `SharePolicy`, `ShareEvent`, `ProviderCase`, `ProviderRequest`, `DigestRun`, `AiCostReport` | `backend/app/contracts.py` | shared (frozen) |
| `main.py` router auto-discovery + deny-by-default role check; stub routers for every endpoint serving `fixtures/` | `backend/app/main.py`, `backend/app/api/*`, `fixtures/` | stubs replaced by owners |
| `auth.py`: working login, JWT cookie, `current_user`, `require_role` | `backend/app/auth.py` | Dev 2 |
| `llm.py`: `call_claude(purpose, model, matter_id, user_id, **kw)` → `ai_runs` | `backend/app/llm.py` | Dev 1 |
| `scripts/smoke.py` (every endpoint vs contracts, as both roles) | `scripts/` | shared |

**Endpoint contract** (owner in brackets; role in braces):
```
[2]{public}   POST /api/auth/login · POST /api/auth/logout · GET /api/auth/me · POST /api/auth/invite/{code}/accept
[1]{attorney} GET /auth/clio/login · /auth/clio/callback · POST /api/sync/{matter_id} · GET /api/sync/status
[1]{attorney} GET /api/matters · /api/matters/{id}/overview · /timeline · /deadlines · /costs · /providers
[1]{attorney} POST /api/matters/{id}/visits → {previous_visit_at} · GET /api/matters/{id}/changes?since= · GET /delta?since=   (F1)
[1]{attorney} GET /api/records/{record_id} · /api/documents/{id}/pages/{n} · /api/documents/{id}/file   (F3)
[1]{attorney} POST /api/digest/{matter_id} → DigestRun · GET /api/matters/{id}/digest-runs   (F9)
[1]{attorney} GET /api/matters/{id}/brief → story, key_moments, injuries, worth, coverage, waiting_on, last_client_contact
[1]{attorney} POST /api/matters/{id}/ask (SSE) · POST /locate · GET /suggested-questions · POST /provider-draft
[1]{attorney} GET /api/ai-costs?matter_id=&from=&to=   (F10)
[2]{attorney} GET /api/matters/{id}/share-candidates?provider_contact_id= · POST /api/shares · POST /api/shares/{grant}/release
[2]{attorney} POST /api/shares/{grant}/revoke · GET /api/shares/{grant}/audit · POST /api/requests/{id}/dismiss
[2]{provider} GET /api/provider/cases · GET /api/provider/cases/{grant} (logs viewed)
[2]{provider} GET /api/provider/cases/{grant}/documents/{doc} (logs document_opened) · POST /api/provider/requests/{id}/complete
```

**Branch and conflict rules**
- Branches: `feat/intelligence` (Dev 1), `feat/product` (Dev 2).
- **Directory ownership:**
  - **Dev 1:** `backend/app/{clio,sync,documents,ai,rag}/`, `api/{sync,matters,records,brief,ask,digest,costs}.py`, `eval/`, `tests/test_{clio_readonly,citations,cache,changes}.py`
  - **Dev 2:** `frontend/`, `backend/app/sharing/`, `api/{auth_routes,shares,provider}.py`, `tests/test_{rbac,sharing}.py`
- **Frozen shared files:** `contracts.py`, `schema.sql`, `main.py`, `db.py`, `llm.py`, `auth.py`. Change them only via a tiny commit to `main` + a message to the other dev, then rebase.
- **The handoff runs through the DB.** Dev 2's projection reads Dev 1's tables read-only; Dev 1 never reads sharing tables.

---

## 6. Workstreams (after Phase 0 → 14:45 freeze), in priority order

### Dev 1: Case Intelligence (`feat/intelligence`)
| # | Task | Done when |
|---|---|---|
| 1.1 | `ClioClient`: OAuth + refresh, **raises on non-GET**, 45 rpm bucket, 429 `Retry-After`, `meta.paging.next`, `fields=` presets | `test_clio_readonly` green |
| 1.2 | Sync of every resource (matter + custom_field_values{…picklist_option}, stage, related_contacts, contacts, notes, communications, tasks, calendar_entries, documents, activities, bills, medical_records_details, medical_bills, damages, matter_stages, users) → `records` with hash / first_seen / last_changed / deleted; incremental `updated_since`; stage/status diff | Sapini in the DB; counts match the Clio UI |
| 1.3 | Documents: download → PyMuPDF page text + PNGs → OCR empty pages (Haiku vision, hash-cached) | every page has text |
| 1.4 | Chunker (sentence units + offsets) → **local bge-base embeddings** → `chunk_vectors` + `chunks_fts` (hash-gated) | re-run embeds 0 |
| 1.5 | Hybrid retrieval + `search_result` builder + citation mapper + evidence verifier (F3) | `test_citations` green |
| 1.6 | Digests (Haiku): one_liner, category, importance + reason, why_it_matters, client_contact, waiting_on, confidential, provider_safe_summary; `digest_runs` + cost logging (F9) | `make cache-demo` → 0 calls on 2nd run |
| 1.7 | Extraction (Opus, verified): injuries + tier, coverage (or NotFound), SOL/DOI, visits, **provider_requests** (F7); `value_model.yaml` + range (F4) | each fact ≥ 1 citation |
| 1.8 | Attorney endpoints: overview, timeline, deadlines, costs, providers, records, pages/file, structured citations, client photo | smoke green on real data |
| 1.9 | **F1** visits + changes + delta; **F2** key moments; story brief; suggested questions (all cached) | edit-in-Clio test passes |
| 1.10 | **Ask** (Opus, tools, SSE, segments + citations, qa_log) + **locate** + provider-draft & classifier | 10 eval Qs, 100% resolvable citations |
| 1.11 | **F10** `/api/ai-costs` aggregation | totals = `SUM(ai_runs.cost_usd)` |
| 1.12 | `eval/` runner → README cost and quality numbers | recorded |

### Dev 2: Product: auth, sharing & frontend (`feat/product`, teammate)
| # | Task | Done when |
|---|---|---|
| 2.1 | (During Phase 0) Next.js scaffold in `frontend/`: Tailwind, shadcn, layout, design tokens; then `make types` from the pushed OpenAPI | app boots against stubs |
| 2.2 | Login + `/invite/[code]` + `middleware.ts` role routing + sign-out; harden `auth.py` (argon2, seed-attorney, invites) | both roles land correctly |
| 2.3 | `<CitationChip>` + popover + `<SourceDrawer>` (text span highlight; PDF page + OCR highlight; prev/next) | any chip → exact span |
| 2.4 | Attorney Brief page: header + photo, **F1** panel (visits → changes → delta; empty and first-visit states), **F4** tiles, spend, deadlines, story, **F2** key moments, injuries/body map, providers & liens, **F9/F10** pill | renders fixtures, then real data |
| 2.5 | **Ask panel**: SSE renderer, segment spans, selection → sources popover, Verify selection, suggestions | highlight → source |
| 2.6 | Backend sharing: grants, versioned policies, `share-candidates`, release (+invite via Resend or console), `ProviderProjection` (alive rule, last movement, coverage, requests, shared docs, unshared keys absent), provider doc serving, `share_events`, audit, revoke, request states (**F5–F8**) | `test_sharing` + `test_rbac` green |
| 2.7 | **F5** Share Composer UI (toggles, doc picker, instant preview using the provider components, AI note, release, revoke) + **F8** audit timeline | toggle → instant preview; release → v+1 |
| 2.8 | Provider app: `/provider/cases`, **F6** heartbeat, **F7** checklist + "Mark sent", shared doc viewer | only released fields render |
| 2.9 | **F10** matter "AI cost" tab (+ `/costs` page, cuttable) | matches the endpoint |
| 2.10 | Deep-Dive swimlanes + full ranked list (stretch) | — |

**Dev 2 works against Phase 0 stubs until the checkpoint.** At the checkpoint it switches to real data: a `.db` copy, or its own `make sync digest`.

---

## 7. Timeline (start ≈ 10:15 → hard stop 4:00)

| Clock | Phase |
|---|---|
| 10:15–10:50 | **Phase 0** (Dev 1) → push `main`. Dev 2 scaffolds `frontend/` in parallel |
| 10:50–12:45 | Round 1 on `feat/intelligence` / `feat/product` |
| 12:45–13:05 | **Checkpoint**: merge both into a throwaway `integration` branch, `make smoke test`, fix drift, rebase; hand over the `.db` (lunch) |
| 13:05–14:45 | Round 2 |
| **14:45** | **Feature freeze.** Delete stubs. Merge `feat/intelligence` → `main`, then `feat/product` → `main`; `make types` |
| 14:45–15:15 | **You run the E2E test (§8)**; owners fix in place |
| 15:15–15:45 | README (stack, data location, models, measured $/case, read-only proof, where to look first), 90-sec video on Sapini |
| ≤ 15:50 | Submit |

- **Cut order if behind:** Deep-Dive → body map → adherence/other-care toggles → email notify → `/costs` firm page → Verify selection.
- **Never cut:** F1–F9, F10 pill + tab, Ask with highlight-to-source, two-role login.

---

## 8. End-to-end test after the final merge

**Setup:**
```
make setup migrate seed-attorney   # uv venv (Py 3.12) + deps, SQLite schema, attorney user
make backend                       # :8000 → log in as attorney → /auth/clio/login → approve
make sync                          # per-resource counts → compare with Clio UI
make digest                        # OCR + local embeddings + digests → prints DigestRun
make frontend                      # :3000
make smoke test                    # contracts (both roles) + rbac + readonly + citations + cache + sharing
```

| # | Check | Expected |
|---|---|---|
| F9 | `make cache-demo` | 2nd run `0 LLM calls · $0.00 · cache hit` |
| F10 | After digest + 3 Asks, open the AI cost tab | total = `SUM(ai_runs.cost_usd)`; 3 Ask rows; cache-hit adds $0.00 |
| F1 | First open → reload → edit a note in Clio → reopen → reopen | "first visit…" → same delta → only that note, with why + chip → "Nothing has changed…" |
| F2 | Key Moments | ≤ 10, each with score + reason + chip; no literals in code |
| F3 | Click every date / $ / injury / claim | excerpt + source identity; drawer highlights the span |
| F4 | Worth + coverage | range labeled Estimate, 3 cited assumptions; "not found in file" where missing |
| RAG | 5 questions; highlight; Verify selection; an out-of-case question | cited stream; selection → sources; honest "not found" |
| F5 | Toggle each field, pick a doc, edit note, Release | instant preview; history v+1 |
| Roles | Incognito: invite → set password → `/provider/cases` | only the granted case |
| F6 | Heartbeat | alive state + last movement; unshared keys absent in JSON |
| F7 | Provider "Mark sent"; attorney view | persists; citation visible to attorney; Clio untouched |
| F8 | Provider opens a doc; attorney audit | released → viewed → document_opened, with actor and time |
| RBAC | As provider: `/api/records/1`, `/api/matters/1/ask`, another grant id | 403 / 403 / 404 |
| Revoke | Revoke → provider reloads | 404 + `revoked` event |

**Rule checks (what judges grep for)**

```
grep -rni "sapini" backend frontend          → none
grep -rn "fixtures" backend/app frontend/app → none (stubs removed)
pytest backend/tests/test_clio_readonly.py   → non-GET raises
```

---

## 9. Open items, settled during Phase 0 / first sync
- **Clio developer app.** Whoever owns the Clio trial registers it (redirect `http://localhost:8000/auth/clio/callback`) and shares client id/secret out of band in `.env`.
- **`ANTHROPIC_API_KEY`** in `.env` on both machines.
- **Resend key** for invites. If there isn't one, the invite link prints to the console.
- **Embeddings** are local (bge-base); the first run downloads the model (~400 MB) on Dev 1's Mac.
- **After the first sync, Dev 1 posts:**
  - which custom fields hold limits, SOL and DOI (mapped semantically, never by name in code)
  - whether PI add-on data is populated
  - whether a client photo exists
