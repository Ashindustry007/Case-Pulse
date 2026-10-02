# Case Pulse — SWANS 2026 Hackathon (Law-Di-Gras)

Cited case digestion for personal-injury firms and the medical providers treating their clients on lien.
Reads Clio Manage **read-only**; every fact on screen links to the note, email or document page it came from.

- Plan & specs: [`docs/PLAN.md`](docs/PLAN.md)
- Workstreams: [`docs/workstreams/`](docs/workstreams/)

## Dev quickstart
```bash
cp .env.example .env            # fill ANTHROPIC_API_KEY, CLIO_*, ATTORNEY_*, JWT_SECRET
make setup migrate seed-attorney
make backend                    # API on :8000 (OpenAPI at /docs)
make frontend                   # UI on :3000
make smoke                      # every endpoint vs contracts, both roles
make test
```
Phase 0 note: endpoints serve synthetic fixtures (`fixtures/`) until each owner replaces its stub with the real implementation.

*(Submission details — stack, data location, models, measured cost per case — are filled in at the end.)*
