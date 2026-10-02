# Workstream 1 — Case Intelligence: Clio, OCR, RAG, AI digestion
**Owner: Dev 1 · branch `feat/intelligence` · runs on Dev 1's Mac (embeddings are local) · master plan: [`docs/PLAN.md`](../PLAN.md). The master plan wins on any conflict.**

> **No pre-existing scaffold.** Phase 0 creates every shared file in the layout from PLAN §5.1. `spec_sheet_v1.md` is superseded by PLAN.md.

---

## 0. Paste this into your Claude Code session to start

```
You are Dev 1 on a 2-person hackathon team (Swans "Law-Di-Gras" Applied AI Hackathon, deadline 4:00 PM today).
Read docs/PLAN.md fully, then docs/workstreams/1-case-intelligence.md (your brief). Follow the brief exactly.
docs/PLAN.md supersedes spec_sheet_v1.md: there is NO pre-existing scaffold; build the repo layout in docs/PLAN.md §5.1.
First do Phase 0 (contract scaffold) on main and push it as "contract: phase-0 scaffold" — Dev 2 is waiting on it.
Then create branch feat/intelligence and execute tasks 1.1 → 1.12 in order, committing after each.
You own: backend/app/{clio,sync,documents,ai,rag}/, backend/app/api/{sync,matters,records,brief,ask,digest,costs}.py,
eval/, backend/tests/test_{clio_readonly,citations,cache,changes}.py. Clio is READ-ONLY (GET only).
Never hardcode case data. Every surfaced fact must carry >=1 verified citation with an excerpt.
```

---

## 1. Mission

Turn one live Clio matter into **cited, cached, cheap intelligence**:
- Sync everything (GET only), OCR every scanned page, and embed locally.
- Digest every record once, extract cited facts, and compute the worth range deterministically.
- Answer questions with **native Claude citations**.
- Expose it all as JSON/SSE endpoints that Dev 2's UI renders.

Every fact must survive the judge clicking it (F3), and the second run must cost $0.00 (F9).

## 2. Ownership and rules

| You own | Read-only for you | Never |
|---|---|---|
| `backend/app/{clio,sync,documents,ai,rag}/**` | `users` (via `auth.py`) | Any non-GET call to Clio (the client raises) |
| `backend/app/api/{sync,matters,records,brief,ask,digest,costs}.py` | | Read or write the sharing tables |
| `eval/**`, `backend/tests/test_{clio_readonly,citations,cache,changes}.py` | | Hardcode case names, fields or moment lists |
| Tables: `records`, `document_pages`, `chunks`, `chunk_vectors`, `chunks_fts`, `digests`, `digest_runs`, `facts`, `briefs`, `provider_requests`, `qa_log`, `ai_runs`, `matter_visits`, `clio_tokens`, `sync_state` | | Emit a fact without a verified citation |

Frozen shared files (`contracts.py`, `schema.sql`, `main.py`, `db.py`, `llm.py`, `auth.py`) are created by you in Phase 0. After that push, change them only via tiny commits to `main` announced to Dev 2.

## 3. Phase 0: contract scaffold (≈ 30 min, on `main`, push immediately)

Create exactly the shared files and directories marked *shared* or *Phase 0* in PLAN §5.1, plus `backend/app/stubs.py` (fixture loader) and empty package dirs for both devs' modules, so neither dev has to create a shared file later.

- **Tooling.** `pyproject.toml` (uv, `requires-python >=3.12`): fastapi, uvicorn[standard], pydantic v2, anthropic, sqlite-vec, fastembed, pymupdf, httpx, argon2-cffi, pyjwt, python-dotenv, rapidfuzz, pyyaml, pytest. `uv python install 3.12`.
- **Makefile:** `setup migrate seed-attorney backend frontend sync digest cache-demo smoke types test`.
- **`.env.example`:**
  - `ANTHROPIC_API_KEY`
  - `CLIO_CLIENT_ID`, `CLIO_CLIENT_SECRET`, `CLIO_REDIRECT_URI=http://localhost:8000/auth/clio/callback`, `CLIO_BASE_URL=https://app.clio.com`
  - `JWT_SECRET`, `ATTORNEY_EMAIL`, `ATTORNEY_PASSWORD`, `ATTORNEY_NAME`
  - `RESEND_API_KEY` (optional), `AI_BUDGET_PER_MATTER_USD=5`
  - `DB_PATH=data/casepulse.db`, `NEXT_PUBLIC_API_URL=http://localhost:8000`
- **`.gitignore`:** add `data/`, `.env`, `.venv/`, `node_modules/`, `.next/`.
- **`backend/db/schema.sql`:** every table in PLAN §1/§4 (SQLite: JSON as TEXT, CHECK enums, ISO timestamps), plus `chunks_fts` (FTS5) and `chunk_vectors` (`vec0`, `embedding float[768]`). Mark each table's owner in a comment.
- **`backend/app/db.py`:** connection factory (WAL, `foreign_keys=ON`, load sqlite-vec), `migrate()`.
- **`backend/app/contracts.py`:** all Pydantic models from PLAN §5, with the `Cited[T]` validator (≥ 1 citation, non-empty excerpt) and `NotFound`.
- **`backend/app/auth.py`:** working login (argon2 + JWT cookie `cp_session`), `current_user`, `require_role`, `public` marker.
- **`backend/app/main.py`:** auto-include every `backend/app/api/*.py` exposing `router`, plus a startup check that each route has a role dependency or the public marker. CORS for `localhost:3000` with credentials.
- **`backend/app/llm.py`:** `call_claude(purpose, model, *, matter_id=None, user_id=None, **kwargs)`. It wraps `anthropic` (streaming variant too) and logs `ai_runs` with tokens, cache-read tokens and cost, using a `PRICES` dict (Opus 5.5 $4/$20, Haiku 4.5 $1/$5 per MTok; cache reads at their discounted rate). It also has `log_local_run(purpose, duration)` for embeddings at $0.
- **Stubs.** Stub routers for **every** endpoint in PLAN §5 (Dev 1 *and* Dev 2 routes), serving `fixtures/<name>.json` validated through the contract models. Fixtures are generic synthetic data with no real case names. SSE stub for `/ask`.
- **`scripts/smoke.py`:** logs in as attorney and as a provider (seeded fixture user in stub mode), hits every endpoint, validates responses, and asserts provider → attorney routes = 403.
- **Commit `contract: phase-0 scaffold`** (with attribution), push `main`, and tell Dev 2.

## 4. Tasks (on `feat/intelligence`), in order

### 1.1 `ClioClient` (`backend/app/clio/`)
- OAuth: `/auth/clio/login` → Clio authorize; `/auth/clio/callback` → token exchange (the only POSTs, to the OAuth host, not the API). Tokens stored in `clio_tokens`; refresh on 401.
- `get(path, params)` / `paginate(path, params)` follow `meta.paging.next`. **`request()` raises `ReadOnlyViolation` for any method ≠ GET to `/api/v4`.**
- Token bucket 45 req/min; on 429, sleep for `Retry-After`. `fields=` presets per resource (nested `{}` syntax).
- **Test** `test_clio_readonly.py`: POST/PATCH/PUT/DELETE raise; GET passes.

### 1.2 Sync (`backend/app/sync/`)
- Matter list → selected matter → pull everything in PLAN §6 task 1.2.
  - Custom fields: `custom_field_values{id,field_name,field_type,value,picklist_option}`.
  - Related contacts with relationship descriptions.
  - Users, to tell internal people from external ones.
- Normalize each item into `records`: `id="{type}:{clio_id}"`, `type, matter_id, title, body_text` (human-readable rendering of the item, including structured fields), `occurred_at, author, participants JSON, raw JSON, content_hash, clio_updated_at`.
- Change tracking: `first_seen_at`, `last_changed_at` (only when the hash changes), `deleted_at` (missing on a full sync). Stage/status diffs produce synthetic `matter_event` records.
- Incremental: `updated_since` from `sync_state`. A `make sync` CLI prints per-resource counts.
- **Then post to Dev 2:** counts, the custom field names found, whether PI add-on data is populated, and whether a client photo exists.

### 1.3 Documents (`backend/app/documents/`)
- Download via `documents/{id}/download` into `data/files/`. PyMuPDF text per page → `document_pages(document_id, page_no, text, method)`. Render a PNG per page into `data/pages/{doc}/{n}.png` (≈ 110 dpi).
- Pages with < 40 chars of text → **OCR via Haiku 4.5 vision** (`purpose=ocr`). Instruction: transcribe faithfully, no summarizing. Cache by image hash.
- Images (jpg/png) in the matter: a Haiku vision check "is this a photo of a person?" gives a client-photo candidate.

### 1.4 Chunk + embed (`backend/app/rag/`)
- Chunk `records.body_text` and each `document_pages.text` into ~400-token chunks with sentence **units** `[{start,end}]` (char offsets into the source text).
- fastembed `BAAI/bge-base-en-v1.5` (768-dim, batched). Queries get the BGE query-instruction prefix.
- Write to `chunk_vectors` (sqlite-vec) + `chunks_fts`. Hash-gated: unchanged chunks are skipped. Duration logged via `log_local_run`.

### 1.5 Retrieval + citations (`backend/app/rag/`)
- `hybrid_search(matter_id, query, types?, date_from?, date_to?, k=12)`: vec KNN 30 + FTS5 bm25 30 → RRF.
- `to_search_results(chunks)`: one `search_result` block per chunk.
  - `source=f"{record_id}#p{page}"`, `title=f"{type}: {title} · {date}"`
  - `content` = one text block per sentence unit, with `citations={"enabled": True}`
  - Keep a side map: `(search_result_index, block_index) → (chunk_id, unit offsets)`.
- `map_citation(search_result_location) → Citation` (exact `char_start/char_end`, excerpt = `cited_text`).
- `verify_evidence(chunk_id, quote) → Citation | None`: rapidfuzz partial match ≥ 90 inside the chunk text, then offsets. **None means the fact is dropped.**
- **Test** `test_citations.py`: block indices map to exact spans; a fabricated quote is dropped; `Cited` with zero citations fails validation.

### 1.6 Digests + instrumentation (F9) (`backend/app/ai/`)
- Haiku 4.5, batched (~15 records per call), structured output per record:
  `one_liner, category, importance 1-10, importance_reason, why_it_matters, client_contact bool, waiting_on?, confidential bool, provider_safe_summary?`
- Each `digests` row stores `content_hash, model, input_tokens, output_tokens, cost_usd`. Skip if the hash is unchanged.
- `digest_runs`: records_seen/changed, llm_calls, tokens, cost, cache_hit.
- `make cache-demo` runs sync+digest twice; the second run prints `0 LLM calls · $0.00 · cache hit`.

### 1.7 Extraction + value model (F4, F7)
- Opus 5.5 (effort low) on retrieved chunks, structured output with `evidence[{chunk_id, quote}]`, verified via 1.5. Extracts:
  - injuries (+ body region, + severity tier soft_tissue|objective|surgical)
  - coverage (carrier, BI per person/accident, UM/UIM, MedPay; absent → `NotFound`)
  - DOI, SOL, treatment visits per provider
  - **provider_requests** (tasks/communications/medical_records_details asking a provider for records, bills or authorizations, with `provider_contact_id`)
- Custom fields are mapped to semantic slots by the LLM from `field_name`, never by hardcoded names.
- `backend/app/ai/value_model.yaml`: generic multiplier bands per tier, with documented rationale. `worth = specials × band`. Specials = Σ medical bills (each a structured citation) + special damages. Add a cap note when limits are found. **The LLM never outputs the number.**
- Facts go to `facts(matter_id, kind, value JSON, citations JSON, input_hash)`, cached by input hash.

### 1.8 Attorney data endpoints (`api/matters.py`, `api/records.py`)
- `overview` (client, photo, status, stage + stages, spend, specials, next deadline, last client contact), `timeline` (+digest join), `deadlines` (overdue/coming/waiting_on), `costs` (expense breakdown + monthly series), `providers` (bills, balance, lien, visits, gaps), `records/{id}`, `documents/{id}/pages/{n}` (+ `image_url`), `documents/{id}/file`.
- Structured facts carry **deterministic citations** to their record (excerpt rendered from fields).

### 1.9 F1 + F2 + brief (`api/brief.py`)
- `POST /visits`: a 30-min session reuses the visit; returns `previous_visit_at`. It also triggers an incremental sync first (time-boxed).
- `GET /changes?since=`: new, changed and removed records ranked by importance, with `why_it_matters` + citations. The response also carries `last_activity` for the explicit empty state.
- `GET /delta?since=`: AI summary of the changes, cached by the hash set.
- Key moments: Opus selects ≤ 10 from digests with importance ≥ 6, with `rank_reason` + verified citations; generic rubric in the prompt.
- Story brief (cited bullets) and suggested questions, all cached by `input_hash` in `briefs`.

### 1.10 Ask + locate + provider draft (`api/ask.py`)
- Opus 5.5 (effort medium), streaming, `tool_choice: auto`.
  - Tools: `search_case(query, types?, date_from?, date_to?)` → `search_result` blocks; `get_case_metrics(kind)` → totals as search_results sourced from the underlying records.
  - System prompt: answer only from case sources; say plainly when something isn't in the file.
- SSE events: `segment {id, text, citations[]}` (one per text block; uncited blocks have `[]`), `done {followups[]}`. Log to `qa_log`.
- `POST /locate {text}`: hybrid search + Haiku entailment per candidate → supporting citations or `{supported:false}`.
- `POST /provider-draft {provider_contact_id, fields}`: use Opus at low effort to draft a provider-safe status note **only from non-confidential digests**, then Haiku confidentiality classifier flags → `{draft, flags[]}`.

### 1.11 AI cost report (F10, `api/costs.py`)
- `GET /api/ai-costs?matter_id=&from=&to=`: totals, by purpose, by model, one-time vs ongoing (ask/locate/draft = ongoing), per-Ask average, cache savings (est. cost of cache-hit skips from the original run's cost), daily series, budget % (`AI_BUDGET_PER_MATTER_USD`).

### 1.12 Eval + README numbers (`eval/`)
- `eval/questions.yaml` (generic phrasing; written after seeing the data) + `eval/run.py`: answer each, check 100% of citations resolve, record latency and cost.
- Report: one-time digestion cost, cost per Ask, citation validity rate. These go into the README and the submission form.

## 5. Definition of done at the freeze (14:45)
- [ ] `pytest backend/tests/test_{clio_readonly,citations,cache,changes}.py` green
- [ ] `make cache-demo` shows the second run at $0.00
- [ ] Every Dev 1 stub and fixture deleted; `grep -rni sapini backend` → nothing
- [ ] Real data on every Dev 1 endpoint; `make smoke` green
- [ ] README numbers recorded (measured $/case, $/Ask, citation validity)
- [ ] Merge `feat/intelligence` → `main` first, then Dev 2 merges

## 6. Never do
- Non-GET calls to Clio, or any write to Clio.
- Emit a fact, date or amount without a verified citation, or invent coverage (use `NotFound`).
- Let the LLM produce the worth number.
- Re-digest unchanged content.
- Hardcode case-specific strings or custom-field names.
