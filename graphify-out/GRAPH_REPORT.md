# Graph Report - .  (2026-10-02)

## Corpus Check
- 164 files · ~95,409 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1400 nodes · 3667 edges · 84 communities (69 shown, 15 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.74)
- Token cost: 221,285 input · 0 output

## Community Hubs (Navigation)
- Sharing & RBAC Tests
- Hackathon Brief & Dev2 Plan
- API Contract Models
- Brief Dashboard Widgets
- Attorney Read Models (views)
- Clio Sync Engine
- App Pages & API Client
- Cost Tab & Audit UI
- Read-only Clio Client
- Sharing Data Adapter
- Brief & F1 Endpoints
- Share Grants & Release
- Worth Model & Assist
- LLM Gateway & Ask
- Ask Panel & Citation UI
- Brief Generation Cache
- Fact Extraction
- Sync Tests & Fake Clio
- Digestion Pipeline
- Provider Endpoints
- TS Compiler Config
- Source Records & Documents
- Layouts & Source Drawer
- Hard Rules & Retrieval Design
- SQLite Access Layer
- Share Composer UI
- Chunking & Local Embeddings
- shadcn Components Config
- Share Endpoints
- Auth & Password Hashing
- Auth Routes
- Settings & Test Fixtures
- Frontend Runtime Deps
- Frontend Dev Deps
- RAG Citation Contract
- Matter Header & Tabs
- Hybrid Search & Metrics
- Record Digests
- Extraction Schemas
- Citation Verification
- Provider Requests & Audit
- Sync API & OAuth
- Plan Timeline & Workstreams
- Provider Projection Spec
- App Bootstrap & Guards
- Cost Instrumentation Spec
- Frontend Route Guard
- Package Scripts
- Models & Worth Spec
- Repo Layout & Contract
- Login & Invite Pages
- Ask API Routes
- Answer Segmentation
- Contract Tests
- Root Layout
- F1 Change Tracking Spec
- Two-Role Auth Spec
- ESLint Config
- ESLint RC Dep
- Next Config
- Theme Dep
- React Dep
- Charts Dep
- Tailwind Dep
- PostCSS Config
- 90-Second Brief
- File Icon
- Globe Icon
- Next.js Logo
- Vercel Logo
- Window Icon
- Python Project

## God Nodes (most connected - your core abstractions)
1. `_Model` - 83 edges
2. `connect()` - 53 edges
3. `now_iso()` - 52 edges
4. `jload()` - 47 edges
5. `api()` - 34 edges
6. `_get()` - 31 edges
7. `jdump()` - 30 edges
8. `Case Pulse Plan (PLAN.md)` - 28 edges
9. `record_citation()` - 26 edges
10. `build_sections()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Rules: read Clio only, no hardcoding, repo is verified` --semantically_similar_to--> `Dev 2 Global Constraints (file ownership, never-edit list)`  [INFERRED] [semantically similar]
  Context-doc/LDG - 8_30 LDG Hackathon.pdf → tasks/todo.md
- `Deny-by-default require_role startup check` --references--> `require_role()`  [EXTRACTED]
  docs/PLAN.md → backend/app/auth.py
- `Case Pulse README (submission)` --references--> `require_role()`  [INFERRED]
  README.md → backend/app/auth.py
- `ReadOnlyViolation on non-GET` --references--> `ReadOnlyViolation`  [EXTRACTED]
  docs/workstreams/1-case-intelligence.md → backend/app/clio/client.py
- `Citation contract type {record_id, source_type, title, author, date, page, char_start, char_end, excerpt}` --references--> `Citation`  [EXTRACTED]
  docs/PLAN.md → backend/app/contracts.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Citation pipeline: retrieval -> search_result -> map/verify -> Cited contract -> chip/drawer** — docs_workstreams_1_case_intelligence_hybrid_search, docs_workstreams_1_case_intelligence_to_search_results, docs_workstreams_1_case_intelligence_map_citation, docs_workstreams_1_case_intelligence_verify_evidence, docs_plan_cited_t_validator, docs_workstreams_2_product_auth_sharing_frontend_citation_chip, docs_workstreams_2_product_auth_sharing_frontend_source_drawer_component [INFERRED 0.85]
- **Provider sharing flow (F5-F8): composer -> release policy -> projection -> heartbeat -> audit** — docs_plan_f5_share_composer, docs_plan_share_policies_versioned, docs_plan_provider_projection, docs_plan_f6_provider_heartbeat, docs_plan_f7_provider_requests, docs_plan_f8_share_audit_trail, docs_plan_share_events_table [EXTRACTED 1.00]
- **Cost instrumentation: llm.py -> ai_runs/digest_runs -> /api/ai-costs -> AI cost UI** — docs_workstreams_1_case_intelligence_llm_py_call_claude, docs_plan_ai_runs_table, docs_plan_digest_runs_table, docs_plan_ai_costs_endpoint, docs_workstreams_2_product_auth_sharing_frontend_ai_cost_ui, docs_plan_cache_demo [INFERRED 0.85]
- **Provider sharing flow: grant -> invite -> release policy -> projection -> provider view -> audit** — tasks_todo_share_grants_release_revoke, tasks_todo_provider_invites, tasks_todo_provider_projection, tasks_todo_provider_access_module, tasks_todo_provider_case_view, tasks_todo_share_events_audit_log [EXTRACTED 0.95]
- **Preview == provider view by construction** — tasks_todo_provider_projection, tasks_todo_apply_policy, tasks_todo_share_composer, tasks_todo_provider_case_view [INFERRED 0.85]
- **Cited attorney brief answering hackathon attorney needs** — context_doc_ldg___8_30_ldg_hackathon_attorney_quotes, tasks_todo_brief_widgets, tasks_todo_citation_ui, backend_app_ai_value_model_case_worth_heuristic, tasks_todo_since_last_visit [INFERRED 0.75]
- **Default create-next-app scaffold public assets (unreferenced by app code)** — frontend_public_file_fileicon, frontend_public_globe_globeicon, frontend_public_next_nextlogo, frontend_public_vercel_vercellogo, frontend_public_window_windowicon [INFERRED 0.85]

## Communities (84 total, 15 thin omitted)

### Community 0 - "Sharing & RBAC Tests"
Cohesion: 0.08
Nodes (54): heartbeat_state(), api(), days_ago(), new_invite(), Factory: api("attorney" | "a" | "b" | None) → TestClient with its own cookie…, Create a grant + invite directly (no release) and return the plaintext code., share(), test_release_rejects_foreign_case_fields() (+46 more)

### Community 1 - "Hackathon Brief & Dev2 Plan"
Cohesion: 0.06
Nodes (52): Case-worth heuristic (F4): specials x injury-tier multiplier, Recovery capped by liability limits note, Injury tiers: soft_tissue 1.5-3.0, objective 2.0-4.0, surgical 3.0-5.0, Attorney needs menu (worth, coverage, spend, since-last-visit, cite every date), Clio Manage (read-only input system), Problem: capturing is solved, digesting the case file is not, Existing tools: Clio Manage, CasePeer, Lawmatics dashboards, Swans Applied AI Hackathon brief (Law-Di-Gras, Oct 2 2026) (+44 more)

### Community 2 - "API Contract Models"
Cohesion: 0.09
Nodes (48): firm_costs(), matter_costs(), Connection, [Dev 1] AI cost monitoring for attorneys (F10). Source of truth: ai_runs (every…, Adherence, AiCostReport, AiRun, Answer (+40 more)

### Community 3 - "Brief Dashboard Widgets"
Cohesion: 0.11
Nodes (33): CoverageTile(), ROWS, DeadlinesBoard(), InjuriesPanel(), regionOf(), REGIONS, KeyMoments(), ProvidersPanel() (+25 more)

### Community 4 - "Attorney Read Models (views)"
Cohesion: 0.12
Nodes (46): client_info(), costs(), _custom_field_date(), _days_between(), deadlines(), _fact(), _FactCitations, _firm_expenses() (+38 more)

### Community 5 - "Clio Sync Engine"
Cohesion: 0.13
Nodes (27): _hash(), MatterSync, Any, _since(), activity(), bill(), calendar_entry(), cf_value() (+19 more)

### Community 6 - "App Pages & API Client"
Cohesion: 0.11
Nodes (27): FirmCosts(), MatterPage(), MattersPage(), SyncStatus, ProviderCasePage(), ProviderCases(), SourceView(), ErrorNote() (+19 more)

### Community 7 - "Cost Tab & Audit UI"
Cohesion: 0.08
Nodes (32): AiCostTab(), SHADES, tok(), AuditTimeline(), LABEL, CostPill(), SinceLastVisit(), components (+24 more)

### Community 8 - "Read-only Clio Client"
Cohesion: 0.09
Nodes (25): clio_callback(), clio_login(), authorize_url(), ClioNotConnected, _drop_field(), exchange_code(), Any, Response (+17 more)

### Community 9 - "Sharing Data Adapter"
Cohesion: 0.11
Nodes (35): BillLine, ProviderBills, ProviderIdentity, SharedDocument, StageShare, WorthEstimate, case_detail_options(), coverage() (+27 more)

### Community 10 - "Brief & F1 Endpoints"
Cohesion: 0.13
Nodes (33): brief(), changes(), delta(), _fmt(), Connection, post, [Dev 1] Brief (F2 key moments, F4 worth/coverage, story), F1…, suggested_questions() (+25 more)

### Community 11 - "Share Grants & Release"
Cohesion: 0.13
Nodes (34): share_candidates(), Grant, PolicyVersionDiff, Everything this provider COULD see, already scoped to them. The composer…, ReleaseResult, ShareAudit, ShareCandidates, SharePolicy (+26 more)

### Community 12 - "Worth Model & Assist"
Cohesion: 0.11
Nodes (30): DraftX, FlagsX, locate(), provider_draft(), BaseModel, Connection, Locate/verify a highlighted passage (RAG highlight-to-source) and draft…, Support (+22 more)

### Community 13 - "LLM Gateway & Ask"
Cohesion: 0.13
Nodes (27): Anthropic, _ocr_one(), OCR for scanned pages (document_pages.method = 'pending') with Claude Haiku…, [Dev 1] Ask the case (RAG, SSE), locate/verify a highlighted passage, provider…, _base_model(), call_claude(), _check(), client() (+19 more)

### Community 14 - "Ask Panel & Citation UI"
Cohesion: 0.11
Nodes (21): AskPanel(), Pop, segKey(), Turn, CitationChip(), useSourceDrawer(), Popover(), PopoverContent() (+13 more)

### Community 15 - "Brief Generation Cache"
Cohesion: 0.16
Nodes (27): _cache_get(), _cache_put(), _candidates(), delta(), ensure_brief(), _first_chunks(), key_moments(), latest() (+19 more)

### Community 16 - "Fact Extraction"
Cohesion: 0.20
Nodes (23): _cached(), _crop(), extract_all(), extract_bills(), extract_coverage(), extract_medical(), extract_requests(), find_client_photo() (+15 more)

### Community 17 - "Sync Tests & Fake Clio"
Cohesion: 0.12
Nodes (20): ClioClient, list_clio_matters(), Sync engine: pull every resource of a matter from Clio (GET only) into…, Sync one matter. Full on first sync (or when asked), incremental afterwards., sync_matter(), main(), CLI: make sync [MATTER=<clio id>] → uv run python -m backend.app.sync [--matter…, F9: an unchanged case is never re-digested — the second digest run makes zero… (+12 more)

### Community 18 - "Digestion Pipeline"
Cohesion: 0.13
Nodes (24): On-open freshness (F1): incremental Clio sync (time-boxed) + incremental…, Start (or join) a refresh; wait up to `wait_seconds` for the sync part. Returns…, _refresh(), refresh_on_open(), ocr_pending_pages(), Connection, main(), _matters() (+16 more)

### Community 19 - "Provider Endpoints"
Cohesion: 0.13
Nodes (24): complete_request(), my_case(), my_cases(), my_document(), Connection, post, [Dev 2] Provider-role endpoints (F6, F7, F8). Output is ONLY…, current_user() (+16 more)

### Community 20 - "TS Compiler Config"
Cohesion: 0.07
Nodes (26): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+18 more)

### Community 21 - "Source Records & Documents"
Cohesion: 0.14
Nodes (24): get_file(), get_page(), get_page_image(), get_record(), Connection, Row, [Dev 1] Source records + document pages/files — the Source Drawer behind every…, _record() (+16 more)

### Community 22 - "Layouts & Source Drawer"
Cohesion: 0.12
Nodes (11): Ctx, SourceCtx, SourceDrawerProvider(), SignOutButton(), Button(), Sheet(), SheetContent(), SheetHeader() (+3 more)

### Community 23 - "Hard Rules & Retrieval Design"
Cohesion: 0.10
Nodes (24): Serena project config (SWANS-2026-Hackathon), ignore_all_files_in_gitignore: true, BAAI/bge-base-en-v1.5 local embeddings (fastembed), GET-only Clio access enforced in code, Hard rules (slide 16): live read, GET-only, no hardcoding, own DB, report $/case, Hybrid retrieval (sqlite-vec KNN + FTS5 bm25 fused with RRF), No hardcoding of case data (no 'Sapini' in code), SQLite (WAL) data/casepulse.db + sqlite-vec + FTS5 (+16 more)

### Community 24 - "SQLite Access Layer"
Cohesion: 0.18
Nodes (21): connect(), get_db(), jdump(), migrate(), _open(), Any, Connection, Path (+13 more)

### Community 25 - "Share Composer UI"
Cohesion: 0.13
Nodes (13): DEFAULT, FIELDS, ShareComposer(), Checkbox(), RadioGroup(), RadioGroupItem(), Textarea(), applyPolicy() (+5 more)

### Community 26 - "Chunking & Local Embeddings"
Cohesion: 0.17
Nodes (20): log_local_run(), Local (free) model runs, e.g. embeddings, logged at $0 so the cost view shows…, _add_unit(), Chunk, chunk_text(), _mk(), Split source text into ~400-token chunks made of sentence UNITS with absolute…, sentence_units() (+12 more)

### Community 27 - "shadcn Components Config"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 28 - "Share Endpoints"
Cohesion: 0.17
Nodes (18): audit(), create_grant(), dismiss_request(), list_grants(), provider_requests(), Connection, post, [Dev 2] Share grants, versioned policies, candidates, audit, attorney request… (+10 more)

### Community 29 - "Auth & Password Hashing"
Cohesion: 0.19
Nodes (18): create_user(), hash_password(), Auth + role guards (shared, FROZEN; Dev 2 owns hardening). - Session: signed…, seed_attorney(), verify_password(), now_iso(), UTC timestamp like 2026-10-02T17:45:00Z (the Z form is safe in query strings,…, accept() (+10 more)

### Community 30 - "Auth Routes"
Cohesion: 0.17
Nodes (19): accept_invite(), login(), logout(), me(), Connection, post, Response, [Dev 2] Auth routes: login/logout/me + provider invite acceptance. (+11 more)

### Community 31 - "Settings & Test Fixtures"
Cohesion: 0.14
Nodes (10): Settings loaded from .env (shared, frozen). Import `settings` everywhere; never…, Settings, fake_clio(), fixture, Test fixtures: every test gets its own throwaway SQLite DB (settings.db_path is…, tmp_db(), FakeClio, _pdf_bytes() (+2 more)

### Community 32 - "Frontend Runtime Deps"
Cohesion: 0.11
Nodes (19): @base-ui/react, class-variance-authority, cn, dependencies, @base-ui/react, class-variance-authority, cn, lucide-react (+11 more)

### Community 33 - "Frontend Dev Deps"
Cohesion: 0.11
Nodes (19): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, openapi-typescript, @tailwindcss/postcss, @types/node (+11 more)

### Community 34 - "RAG Citation Contract"
Cohesion: 0.14
Nodes (17): Agentic Ask tools: search_case, get_case_metrics, Answer contract {segments[{id,text,citations}], followups}, Ask the case (RAG) with highlight-to-source, Citation contract type {record_id, source_type, title, author, date, page, char_start, char_end, excerpt}, Cited[T] validator (>=1 citation with non-empty excerpt), Evidence quote verification (fuzzy match, unverified facts dropped), F3 Click-to-source citations, /locate 'Verify selection' (retrieval + Haiku entailment) (+9 more)

### Community 35 - "Matter Header & Tabs"
Cohesion: 0.21
Nodes (12): BriefGrid(), MatterHeader(), Chips(), Cited(), Tabs(), TabsContent(), TabsList(), tabsListVariants (+4 more)

### Community 36 - "Hybrid Search & Metrics"
Cohesion: 0.22
Nodes (13): _metrics(), Connection, Exact totals computed from structured records; returned with those records as…, Tracks every search_result block sent in a conversation, in order…, ResultRegistry, _fts_ids(), fts_query(), Hit (+5 more)

### Community 38 - "Record Digests"
Cohesion: 0.24
Nodes (14): _digest_batches(), digest_input_hash(), digest_matter(), DigestBatch, _item_text(), ItemDigest, BaseModel, Connection (+6 more)

### Community 39 - "Extraction Schemas"
Cohesion: 0.24
Nodes (14): BillsX, BillX, CoverageFieldX, CoverageX, DateX, Evidence, InjuryX, MedicalX (+6 more)

### Community 40 - "Citation Verification"
Cohesion: 0.25
Nodes (13): _align(), _citation(), citations_from_json(), Any, Connection, Row, Citations (F3): every path that produces a `Citation` lives here. 1. RAG: hits…, Cite a whole line of a record: the line containing `contains`, else the first… (+5 more)

### Community 41 - "Provider Requests & Audit"
Cohesion: 0.15
Nodes (15): F7 What the firm needs from me (provider requests), F8 Share audit trail, provider_requests table, request_states table, share_events table (append-only), Dev 1 read helpers (views.provider_summaries, open_requests, value.coverage, value.worth, stage_info), Sharing backend task 2.6 (grants, policies, projection, events), test_rbac.py + test_sharing.py (+7 more)

### Community 42 - "Sync API & OAuth"
Cohesion: 0.19
Nodes (12): Connection, post, [Dev 1] Clio connection (OAuth) + sync endpoints. Clio is read-only input., run_sync(), sync_status(), Route guard. Usage: APIRouter(dependencies=[Depends(require_role("attorney"))])., require_role(), SyncResult (+4 more)

### Community 43 - "Plan Timeline & Workstreams"
Cohesion: 0.16
Nodes (14): Case Pulse Plan (PLAN.md), Cut order if behind / never cut list, Handoff runs through the DB (Dev 2 reads Dev 1 tables read-only), Dev 1: Case Intelligence workstream (feat/intelligence), Dev 2: Product workstream (feat/product), End-to-end test after final merge (PLAN §8), Frozen shared files (contracts.py, schema.sql, main.py, db.py, llm.py, auth.py), Invite link -> provider sets password provisioning (+6 more)

### Community 44 - "Provider Projection Spec"
Cohesion: 0.23
Nodes (13): F5 Share composer with live provider preview, F6 Provider case heartbeat, ProviderProjection (whitelist builder), digests.provider_safe_summary, GET /share-candidates (provider-scoped sections), share_policies (versioned release policy), Ask + locate + provider-draft task 1.10, POST /provider-draft (Opus draft + Haiku confidentiality classifier) (+5 more)

### Community 45 - "App Bootstrap & Guards"
Cohesion: 0.24
Nodes (7): public(), Explicit marker for routes that need no session (login, invite accept, OAuth…, _assert_all_routes_guarded(), _has_guard(), health(), _include_routers(), FastAPI app (shared, FROZEN). Nobody registers routes here: every module in…

### Community 46 - "Cost Instrumentation Spec"
Cohesion: 0.24
Nodes (10): GET /api/ai-costs, ai_runs table (per-call cost log), make cache-demo (2nd run 0 LLM calls), digest_runs table, F10 LLM cost monitoring for attorneys, F9 Digest caching + cost-per-case instrumentation, Digests task 1.6 (Haiku batched per-record structured output), llm.py call_claude / log_local_run with PRICES (+2 more)

### Community 47 - "Frontend Route Guard"
Cohesion: 0.33
Nodes (6): GuardRole, HOME, roleFromToken(), routeDecision(), config, middleware()

### Community 48 - "Package Scripts"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, dev, lint, start, test (+1 more)

### Community 49 - "Models & Worth Spec"
Cohesion: 0.25
Nodes (9): claude-haiku-4-5 (OCR, digests, entailment), claude-opus-5-5 (Ask, extraction, key moments, brief), F2 Key moments (the 10 from 300), F4 Case worth + coverage KPIs, 'Not found in file' (NotFound) rendering, value_model.yaml multiplier bands, Extraction + value model task 1.7 (Opus, verified evidence), facts table (cached by input hash) (+1 more)

### Community 50 - "Repo Layout & Contract"
Cohesion: 0.22
Nodes (9): Endpoint contract (owners and roles), Repo layout (PLAN §5.1), Workstream 2 brief: Product, Auth, Sharing & Frontend, Deep-Dive swimlanes task 2.10 (stretch), Frontend scaffold task 2.1 (Next.js 15, Tailwind, shadcn/ui), make types (OpenAPI -> frontend/lib/api-types.ts), Dev 2 mission: users, sharing, pixels, Frontend README (create-next-app boilerplate) (+1 more)

### Community 51 - "Login & Invite Pages"
Cohesion: 0.39
Nodes (3): Input(), Label(), UserOut

### Community 53 - "Ask API Routes"
Cohesion: 0.32
Nodes (8): ask(), locate(), provider_draft(), Connection, post, AskRequest, LocateRequest, ProviderDraftRequest

### Community 54 - "Answer Segmentation"
Cohesion: 0.29
Nodes (7): AnswerSegment, block_segment(), Any, Cheap heuristic follow-ups from what the answer cited (no extra LLM call)., Merge segments into lines/bullets; drop lines that carry no citation (F3:…, segments_to_sentences(), suggest_followups()

### Community 56 - "Root Layout"
Cohesion: 0.33
Nodes (4): geistMono, geistSans, metadata, Toaster()

### Community 57 - "F1 Change Tracking Spec"
Cohesion: 0.40
Nodes (6): Case Pulse, Clio Manage (v4 API), F1 Changed since your last visit digest, matter_visits table, records table (change tracking: first_seen_at, last_changed_at, deleted_at, content_hash), Sync task 1.2 (records normalization, change tracking, matter_event)

### Community 58 - "Two-Role Auth Spec"
Cohesion: 0.60
Nodes (5): Deny-by-default require_role startup check, JWT httpOnly SameSite=Lax cookie session (user reloaded per request), Next.js middleware.ts role routing (UX only), Two-role auth (attorney admin / provider scoped), Auth task 2.2 (argon2, PyJWT cp_session cookie, invites)

### Community 60 - "ESLint Config"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

## Ambiguous Edges - Review These
- `SQLite (WAL) data/casepulse.db + sqlite-vec + FTS5` → `ignore_all_files_in_gitignore: true`  [AMBIGUOUS]
  .serena/project.yml · relation: conceptually_related_to
- `Generic attorney eval questions (case-agnostic, 10)` → `Rules: read Clio only, no hardcoding, repo is verified`  [AMBIGUOUS]
  eval/questions.yaml · relation: rationale_for

## Knowledge Gaps
- **156 isolated node(s):** `SyncStatus`, `geistSans`, `geistMono`, `metadata`, `style` (+151 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `SQLite (WAL) data/casepulse.db + sqlite-vec + FTS5` and `ignore_all_files_in_gitignore: true`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Generic attorney eval questions (case-agnostic, 10)` and `Rules: read Clio only, no hardcoding, repo is verified`?**
  _Edge tagged AMBIGUOUS (relation: rationale_for) - confidence is low._
- **Why does `now_iso()` connect `Auth & Password Hashing` to `Sharing & RBAC Tests`, `API Contract Models`, `Record Digests`, `Extraction Schemas`, `Read-only Clio Client`, `Brief & F1 Endpoints`, `Share Grants & Release`, `Worth Model & Assist`, `LLM Gateway & Ask`, `Sync API & OAuth`, `Brief Generation Cache`, `Fact Extraction`, `Sync Tests & Fake Clio`, `Digestion Pipeline`, `Provider Endpoints`, `SQLite Access Layer`, `Chunking & Local Embeddings`, `Share Endpoints`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `Case Pulse README (submission)` connect `Hard Rules & Retrieval Design` to `Plan Timeline & Workstreams`, `Sync API & OAuth`, `API Contract Models`, `Cost Instrumentation Spec`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `jload()` connect `Attorney Read Models (views)` to `Hybrid Search & Metrics`, `Extraction Schemas`, `Citation Verification`, `Sharing Data Adapter`, `Brief & F1 Endpoints`, `Share Grants & Release`, `Worth Model & Assist`, `Brief Generation Cache`, `Fact Extraction`, `Provider Endpoints`, `Source Records & Documents`, `SQLite Access Layer`, `Share Endpoints`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **What connects `SyncStatus`, `geistSans`, `geistMono` to the rest of the system?**
  _156 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Sharing & RBAC Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.07987012987012987 - nodes in this community are weakly interconnected._