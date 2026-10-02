# Case Pulse — SWANS 2026 Hackathon (Law-Di-Gras)

Cited case digestion for personal-injury firms and the medical providers treating their clients on lien.
Reads Clio Manage **read-only**; every date, dollar figure, injury and claim on screen links to the exact note, email
or document page span it came from.

- Plan & specs: [`docs/PLAN.md`](docs/PLAN.md) · Workstreams: [`docs/workstreams/`](docs/workstreams/)

## Where to look first
| What | Where |
|---|---|
| Read-only Clio client (any non-GET raises) | [`backend/app/clio/client.py`](backend/app/clio/client.py) · test [`test_clio_readonly.py`](backend/tests/test_clio_readonly.py) |
| Citations: Claude `search_result` blocks → exact source spans; model quotes verified or dropped | [`backend/app/rag/cite.py`](backend/app/rag/cite.py), [`backend/app/rag/answer.py`](backend/app/rag/answer.py) |
| "No fact without a citation" enforced by the API contract | `Cited[T]` in [`backend/app/contracts.py`](backend/app/contracts.py) |
| Hash-gated digestion pipeline + per-stage cost accounting | [`backend/app/ai/pipeline.py`](backend/app/ai/pipeline.py) |
| Case-worth range: deterministic code over cited inputs (the LLM never outputs the number) | [`backend/app/ai/value.py`](backend/app/ai/value.py), [`value_model.yaml`](backend/app/ai/value_model.yaml) |
| Deny-by-default role guards (attorney / provider) | [`backend/app/auth.py`](backend/app/auth.py), [`backend/app/main.py`](backend/app/main.py) |

## Tech stack
- **Built with:** Python 3.12 + FastAPI (backend), Next.js 15 + Tailwind + shadcn/ui (frontend), Anthropic Python SDK.
- **Runs on:** localhost (backend `:8000`, frontend `:3000`).
- **Data outside Clio:** one local SQLite file (`data/casepulse.db`, WAL) with **sqlite-vec** (vectors) and **FTS5**
  (keyword search); downloaded documents and page images under `data/`. Nothing is ever written back to Clio.
- **Embeddings:** local `BAAI/bge-base-en-v1.5` via fastembed — case text never leaves the machine for embedding.

## AI models and cost per case (measured on the Sapini matter)
| Model | Used for |
|---|---|
| `claude-haiku-4-5` | OCR of scanned pages (vision), per-record digests (importance, why-it-matters, confidentiality), photo detection |
| `claude-opus-5-5` | Cited extraction (injuries, coverage, dates, bills, provider requests), key moments, story, Ask the case |
| `BAAI/bge-base-en-v1.5` (local) | Embeddings for hybrid retrieval (vector + BM25) |

Sapini: 203 records, 31 documents / 361 pages (10 image-only pages OCR'd), 706 retrieval chunks.

| Run | LLM calls | Cost |
|---|---|---|
| **First full digestion of the case** | 38 | **$1.10** |
| Re-open / re-run with no changes (cache hit) | **0** | **$0.00** |
| Incremental refresh after 14 records changed in Clio | 5 | $0.22 |
| One "Ask the case" question (avg of 10, with tool use + citations) | 1–3 | $0.135 (avg 16 s) |

Every call is logged to `ai_runs` (tokens, $, cache hits, savings) and shown to attorneys in the AI-cost view.

**Ask-the-case eval** ([`eval/results.md`](eval/results.md)): 10 generic attorney questions → **147/147 citations
(100%) resolve to the exact source text** at their stored offsets; out-of-file questions are answered "not in the file".

## Quickstart
```bash
cp .env.example .env            # ANTHROPIC_API_KEY, CLIO_CLIENT_ID/SECRET (redirect http://127.0.0.1:8000/auth/clio/callback)
make setup migrate seed-attorney
make backend                    # API on :8000 (OpenAPI at /docs)
make clio-connect               # open the printed link once, approve read access
make sync                       # pull every matter (read-only)
make digest                     # OCR + embeddings + AI digestion (incremental)
make cache-demo                 # 2nd run: 0 LLM calls · $0.00
make frontend                   # UI on :3000
make smoke test                 # every endpoint as both roles + unit tests
```

## Notes for judges
- **Nothing is hardcoded to Sapini:** `grep -rni sapini backend frontend` returns nothing. Custom fields are mapped
  semantically by the model; moments, injuries and requests are extracted from the records each run.
- The trial account returns **403 for the Personal Injury add-on endpoints** (`medical_records_details`, `damages`).
  The sync handles that gracefully; medical bills are extracted (with citations) from the itemized-bill PDFs instead —
  their sum ($118,400) independently matches the matter's own "Medical Specials To Date" field.
- Client medical charges that the file records as *expense entries* are excluded from "firm spend" (shown: $1,410 of
  actual firm costs).
