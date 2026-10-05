# Case Pulse — common commands. Backend: uv + Python 3.12. Frontend: Next.js (frontend/).
.PHONY: demo demo-data export-demo clio-connect clio-code setup migrate seed-attorney backend frontend sync digest cache-demo smoke types test

PY := uv run python

setup:            ## install backend deps (and frontend deps if present)
	uv sync
	@if [ -f frontend/package.json ]; then cd frontend && npm install; fi

demo:             ## fresh clone → ready to run on the bundled Sapini case (no Clio account needed)
	$(MAKE) setup demo-data migrate seed-attorney
	@echo "Now run 'make backend' and 'make frontend' in two terminals, then open http://localhost:3000"

demo-data:        ## install the bundled, already-digested case as data/casepulse.db (never overwrites an existing one)
	@if [ -f data/casepulse.db ]; then echo "data/casepulse.db already exists - leaving it alone"; \
	else cp data/casepulse.demo.db data/casepulse.db && echo "installed data/casepulse.db from data/casepulse.demo.db"; fi

export-demo:      ## refresh data/casepulse.demo.db from your live DB, with tokens/logins stripped (then commit it)
	$(PY) -m scripts.export_demo_db

migrate:          ## create/upgrade the SQLite schema (data/casepulse.db)
	$(PY) -m backend.app.db

seed-attorney:    ## create the attorney user from .env (ATTORNEY_EMAIL / ATTORNEY_PASSWORD)
	$(PY) -m backend.app.auth seed-attorney

backend:          ## API on :8000
	uv run uvicorn backend.app.main:app --reload --port 8000

frontend:         ## UI on :3000
	cd frontend && npm run dev

clio-connect:     ## print a Clio OAuth link (backend must be running)
	$(PY) -m backend.app.clio.connect $(if $(MANUAL),manual,)

clio-code:        ## exchange a code from Clio's approval page: make clio-code CODE=...
	$(PY) -m backend.app.clio.connect code $(CODE)

sync:             ## pull every matter from Clio (READ-ONLY). MATTER=<clio id> to limit
	$(PY) -m backend.app.sync $(if $(MATTER),--matter $(MATTER),)

digest:           ## OCR + embeddings + AI digestion (incremental, hash-cached). MATTER=<id> to limit
	$(PY) -m backend.app.ai.pipeline $(if $(MATTER),--matter $(MATTER),)

cache-demo:       ## F9: run digest twice; 2nd run must be 0 LLM calls / $0.00
	$(PY) -m backend.app.ai.pipeline --cache-demo $(if $(MATTER),--matter $(MATTER),)

smoke:            ## hit every endpoint as attorney and provider; validate against contracts (backend must be running)
	$(PY) scripts/smoke.py

types:            ## regenerate frontend API types from the running backend's OpenAPI
	cd frontend && npx openapi-typescript http://localhost:8000/openapi.json -o lib/api-types.ts

test:             ## unit tests
	uv run pytest -q
