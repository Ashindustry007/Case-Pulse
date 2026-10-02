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
