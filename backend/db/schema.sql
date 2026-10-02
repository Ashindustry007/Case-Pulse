-- Case Pulse schema (SQLite, WAL). FROZEN shared file: change only via a small commit to main + tell the other dev.
-- Conventions: ids from Clio are INTEGER; our own record ids are TEXT "{type}:{clio_id}".
-- JSON stored as TEXT (query with json_extract). Timestamps are ISO-8601 TEXT (UTC).
-- Owner per table: [1] = Dev 1 (case intelligence), [2] = Dev 2 (product), [S] = shared.

PRAGMA foreign_keys = ON;

------------------------------------------------------------------------------------------
-- [1] Clio connection + sync bookkeeping
------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clio_tokens (
  id            INTEGER PRIMARY KEY CHECK (id = 1),
  access_token  TEXT NOT NULL,
  refresh_token TEXT,
  expires_at    TEXT,
  clio_user     TEXT,              -- JSON: who connected (Clio "who_am_i")
  updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sync_state (
  matter_id      INTEGER NOT NULL,
  resource       TEXT NOT NULL,
  last_synced_at TEXT NOT NULL,
  item_count     INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (matter_id, resource)
);

------------------------------------------------------------------------------------------
-- [1] Mirrored from Clio (read-only copies)
------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS matters (
  id             INTEGER PRIMARY KEY,   -- Clio matter id
  display_number TEXT,
  description    TEXT,
  status         TEXT,                  -- open | pending | closed
  stage_id       INTEGER,
  stage_name     TEXT,
  practice_area  TEXT,
  client_id      INTEGER,               -- Clio contact id
  open_date      TEXT,
  close_date     TEXT,
  clio_url       TEXT,
  raw            TEXT,                  -- JSON
  synced_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matter_stages (
  id            INTEGER PRIMARY KEY,
  name          TEXT NOT NULL,
  practice_area TEXT,
  sort_order    INTEGER
);

CREATE TABLE IF NOT EXISTS contacts (
  id          INTEGER PRIMARY KEY,      -- Clio contact id
  name        TEXT,
  type        TEXT,                     -- Person | Company
  email       TEXT,
  phone       TEXT,
  avatar_url  TEXT,
  raw         TEXT,                     -- JSON
  synced_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matter_contacts (
  matter_id    INTEGER NOT NULL,
  contact_id   INTEGER NOT NULL,
  relationship TEXT NOT NULL DEFAULT '',   -- e.g. "Client", "Treating Physician", "Insurance Adjuster"
  is_client    INTEGER NOT NULL DEFAULT 0,
  role         TEXT,                       -- normalized: client | medical_provider | insurer | attorney | other
  PRIMARY KEY (matter_id, contact_id, relationship)
);

CREATE TABLE IF NOT EXISTS firm_users (       -- Clio users (internal staff), to tell internal from external
  id    INTEGER PRIMARY KEY,
  name  TEXT,
  email TEXT,
  raw   TEXT
);

-- Every citable item of the case, normalized. One row per Clio item (or synthetic event).
CREATE TABLE IF NOT EXISTS records (
  id              TEXT PRIMARY KEY,         -- "{type}:{clio_id}"
  matter_id       INTEGER NOT NULL,
  type            TEXT NOT NULL CHECK (type IN (
                    'note','communication','task','calendar_entry','document','expense','time_entry',
                    'bill','medical_record','medical_bill','damage','custom_field','matter_event','contact')),
  clio_id         TEXT,
  title           TEXT,
  body_text       TEXT NOT NULL DEFAULT '', -- human-readable rendering; citations index into this (or into document_pages.text)
  occurred_at     TEXT,                     -- when it happened (note date, email sent, due date, bill date...)
  author          TEXT,
  participants    TEXT,                     -- JSON array of {name, email, contact_id, role}
  meta            TEXT,                     -- JSON: type-specific structured fields (amount, due_at, status, provider_contact_id...)
  raw             TEXT,                     -- JSON from Clio
  clio_url        TEXT,
  content_hash    TEXT NOT NULL,
  clio_updated_at TEXT,
  first_seen_at   TEXT NOT NULL,
  last_changed_at TEXT NOT NULL,            -- only moves when content_hash changes
  deleted_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_records_matter ON records(matter_id, type);
CREATE INDEX IF NOT EXISTS idx_records_changed ON records(matter_id, last_changed_at);

CREATE TABLE IF NOT EXISTS document_pages (
  document_id TEXT NOT NULL,                -- records.id of type 'document'
  page_no     INTEGER NOT NULL,             -- 1-based
  text        TEXT NOT NULL DEFAULT '',
  method      TEXT NOT NULL CHECK (method IN ('text_layer','ocr','none','pending')),
  image_path  TEXT,                         -- data/pages/{doc}/{n}.png
  text_hash   TEXT,
  PRIMARY KEY (document_id, page_no)
);

------------------------------------------------------------------------------------------
-- [1] Retrieval index
------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chunks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  matter_id    INTEGER NOT NULL,
  record_id    TEXT NOT NULL,
  page_no      INTEGER,                     -- set for document pages
  char_start   INTEGER NOT NULL,            -- offsets into records.body_text or document_pages.text
  char_end     INTEGER NOT NULL,
  text         TEXT NOT NULL,
  units        TEXT NOT NULL,               -- JSON [[start,end],...] sentence units, absolute offsets in the source text
  content_hash TEXT NOT NULL,
  created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_record ON chunks(record_id);
CREATE INDEX IF NOT EXISTS idx_chunks_matter ON chunks(matter_id);
-- FTS5 + sqlite-vec virtual tables use rowid = chunks.id (created in db.py so the extension is loaded first)

------------------------------------------------------------------------------------------
-- [1] AI outputs (all cached by input hash)
------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS digests (
  record_id             TEXT PRIMARY KEY,
  matter_id             INTEGER NOT NULL,
  content_hash          TEXT NOT NULL,
  one_liner             TEXT,
  category              TEXT,
  importance            INTEGER,            -- 1..10
  importance_reason     TEXT,
  why_it_matters        TEXT,
  client_contact        INTEGER NOT NULL DEFAULT 0,
  waiting_on            TEXT,               -- who the firm is waiting on, if any
  confidential          INTEGER NOT NULL DEFAULT 0,   -- strategy / settlement / internal → never provider-visible
  provider_safe_summary TEXT,               -- plain-language, non-confidential summary (null if confidential)
  model                 TEXT,
  input_tokens          INTEGER NOT NULL DEFAULT 0,
  output_tokens         INTEGER NOT NULL DEFAULT 0,
  cost_usd              REAL NOT NULL DEFAULT 0,
  created_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_digests_matter ON digests(matter_id, importance);

CREATE TABLE IF NOT EXISTS digest_runs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  matter_id       INTEGER NOT NULL,
  trigger         TEXT NOT NULL,            -- manual | on_open | cache_demo | api
  started_at      TEXT NOT NULL,
  finished_at     TEXT,
  records_seen    INTEGER NOT NULL DEFAULT 0,
  records_changed INTEGER NOT NULL DEFAULT 0,
  llm_calls       INTEGER NOT NULL DEFAULT 0,
  input_tokens    INTEGER NOT NULL DEFAULT 0,
  output_tokens   INTEGER NOT NULL DEFAULT 0,
  cost_usd        REAL NOT NULL DEFAULT 0,
  cache_hit       INTEGER NOT NULL DEFAULT 0,
  stages          TEXT                      -- JSON {stage: {items, llm_calls, cost_usd, skipped}}
);

CREATE TABLE IF NOT EXISTS facts (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  matter_id  INTEGER NOT NULL,
  kind       TEXT NOT NULL,                 -- injury | coverage | doi | sol | treatment_visit | worth_inputs | client_photo ...
  value      TEXT NOT NULL,                 -- JSON
  citations  TEXT NOT NULL,                 -- JSON [Citation]; never empty for surfaced facts
  input_hash TEXT NOT NULL,
  model      TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_matter ON facts(matter_id, kind);

CREATE TABLE IF NOT EXISTS briefs (
  matter_id  INTEGER NOT NULL,
  kind       TEXT NOT NULL,                 -- story | key_moments | delta | suggested_questions | extraction
  input_hash TEXT NOT NULL,
  content    TEXT NOT NULL,                 -- JSON
  created_at TEXT NOT NULL,
  PRIMARY KEY (matter_id, kind, input_hash)
);

CREATE TABLE IF NOT EXISTS provider_requests (
  id                  TEXT PRIMARY KEY,     -- stable hash of (matter, provider, kind, source)
  matter_id           INTEGER NOT NULL,
  provider_contact_id INTEGER,
  provider_name       TEXT,
  kind                TEXT NOT NULL CHECK (kind IN ('records','bills','authorization','other')),
  description         TEXT NOT NULL,
  requested_at        TEXT,
  channel             TEXT,                 -- task | email | records_request
  source_addressed_to_provider INTEGER NOT NULL DEFAULT 0,  -- 1 if the source message was sent to the provider (excerpt may be shown to them)
  citations           TEXT NOT NULL,        -- JSON [Citation], never empty
  input_hash          TEXT NOT NULL,
  created_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_requests_provider ON provider_requests(matter_id, provider_contact_id);

CREATE TABLE IF NOT EXISTS qa_log (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  matter_id  INTEGER NOT NULL,
  user_id    INTEGER,
  question   TEXT NOT NULL,
  answer     TEXT NOT NULL,                 -- JSON Answer
  cost_usd   REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_runs (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  matter_id          INTEGER,
  user_id            INTEGER,
  purpose            TEXT NOT NULL CHECK (purpose IN
                       ('ocr','embed','digest','extract','brief','key_moments','delta','ask','locate','draft','classify','vision','other')),
  model              TEXT NOT NULL,
  input_tokens       INTEGER NOT NULL DEFAULT 0,
  output_tokens      INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens  INTEGER NOT NULL DEFAULT 0,
  cache_write_tokens INTEGER NOT NULL DEFAULT 0,
  cost_usd           REAL NOT NULL DEFAULT 0,
  duration_ms        INTEGER,
  cache_hit          INTEGER NOT NULL DEFAULT 0,   -- 1 = skipped because cached (cost 0, saved_usd estimated)
  saved_usd          REAL NOT NULL DEFAULT 0,
  created_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ai_runs_matter ON ai_runs(matter_id, created_at);

CREATE TABLE IF NOT EXISTS matter_budgets (
  matter_id  INTEGER PRIMARY KEY,
  budget_usd REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS matter_visits (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id           INTEGER NOT NULL,
  matter_id         INTEGER NOT NULL,
  visited_at        TEXT NOT NULL,           -- start of this visit/session
  last_seen_at      TEXT NOT NULL,           -- refreshed on reload; reloads within 30 min reuse the visit
  previous_visit_at TEXT                     -- baseline for "changed since your last visit"
);
CREATE INDEX IF NOT EXISTS idx_visits ON matter_visits(user_id, matter_id, visited_at);

------------------------------------------------------------------------------------------
-- [2] Users, auth, sharing (Dev 2 owns; created here so the schema is complete from Phase 0)
------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  email               TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash       TEXT NOT NULL,
  name                TEXT,
  role                TEXT NOT NULL CHECK (role IN ('attorney','provider')),
  provider_contact_id INTEGER,              -- Clio contact id for provider users
  created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS share_grants (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  matter_id           INTEGER NOT NULL,
  provider_contact_id INTEGER NOT NULL,
  provider_name       TEXT,
  email               TEXT NOT NULL,
  provider_user_id    INTEGER REFERENCES users(id),
  created_by          INTEGER REFERENCES users(id),
  created_at          TEXT NOT NULL,
  revoked_at          TEXT
);

CREATE TABLE IF NOT EXISTS share_policies (
  grant_id        INTEGER NOT NULL REFERENCES share_grants(id),
  version         INTEGER NOT NULL,
  fields          TEXT NOT NULL,            -- JSON array of ShareField
  document_ids    TEXT NOT NULL DEFAULT '[]',
  coverage_detail TEXT NOT NULL DEFAULT 'confirmed' CHECK (coverage_detail IN ('confirmed','limits')),
  status_note     TEXT,
  released_by     INTEGER REFERENCES users(id),
  released_at     TEXT NOT NULL,
  PRIMARY KEY (grant_id, version)
);

CREATE TABLE IF NOT EXISTS invites (
  code_hash  TEXT PRIMARY KEY,              -- sha256 of the invite code
  email      TEXT NOT NULL,
  grant_id   INTEGER REFERENCES share_grants(id),
  expires_at TEXT NOT NULL,
  used_at    TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS share_events (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  grant_id       INTEGER NOT NULL REFERENCES share_grants(id),
  policy_version INTEGER,
  event          TEXT NOT NULL CHECK (event IN ('released','viewed','document_opened','request_completed',
                                                'request_dismissed','revoked','invite_sent','invite_accepted')),
  actor_user_id  INTEGER,
  actor_email    TEXT,
  at             TEXT NOT NULL,
  meta           TEXT                       -- JSON
);
CREATE INDEX IF NOT EXISTS idx_share_events ON share_events(grant_id, at);

CREATE TABLE IF NOT EXISTS request_states (
  request_id TEXT PRIMARY KEY,              -- provider_requests.id
  state      TEXT NOT NULL CHECK (state IN ('open','completed','dismissed')),
  by_user_id INTEGER,
  at         TEXT NOT NULL,
  note       TEXT
);
