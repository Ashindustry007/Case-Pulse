# Build Spec — "The 90-Second Case File"
### Law-Di-Gras Applied AI Hackathon · One matter: Sapini (Clio Manage) · Deadline 4:00 PM

This document is the complete build brief for the coding agent. It describes **what** to build and **why**, with checkable acceptance criteria per feature. It deliberately contains no code-level implementation details — the agent chooses the implementation.

---

## 0. The product in one paragraph

A case-digest dashboard that turns a live personal-injury case file into something a human absorbs in ninety seconds. It has **two access levels**: an **Administrator view** for the firm's attorneys (full access, full control) and a **restricted Medical Provider view** provisioned by the attorneys (sees only what the firm explicitly shares). One underlying case model, two rendered views, and an attorney-controlled membrane between them. This is a visual digestion of the case — **not** a chat interface.

---

## 1. Hard rules (from the hackathon brief — non-negotiable)

1. **Clio is read-only input.** The app may call Clio READ APIs only. Never create, update, or delete anything in Clio. ("Read everything, write nothing.")
2. **All app-side CRUD happens in OUR database.** Share policies, visit tracking, audit logs, digests, caches — all read/write against the local database, never Clio.
3. **One matter: Sapini.** Everything must work live against the team's Clio Manage account. Nothing may be hardcoded to Sapini's contents — the screeners check for this.
4. **Localhost demo is acceptable.** A live link is optional.
5. **Submission = repo + 90-second clip + tech stack + AI models used + approximate cost to run one case.** The cost-per-case number must be real, so instrument it during the build.

---

## 2. System architecture

```
Clio Manage (READ-ONLY source of truth)
        │  read-only API pulls
        ▼
Ingestion service ──► Local database (the app's read/write store)
        │                    │
        │              Digest pipeline (LLM: moments, KPIs, citations)
        │                    │
        ▼                    ▼
              Next.js app (two roles: Admin / Provider)
```

- **Ingestion** pulls every entity for the matter from Clio, extracts text from documents (OCR for scanned PDFs — the brief warns that key facts hide inside 200-page scans), and stores normalized rows locally.
- **Refresh strategy:** an on-demand "Sync now" plus a content hash per record. New or changed records invalidate the cached digest. The app never queries Clio at request time; it always reads the local database.
- **Digest caching:** a digest is stored per (matter + content hash). If nothing changed since the last digest, serve the cached one — never re-run the AI over an unchanged case. (The brief quotes this complaint verbatim.)
- **Wire new logic through `problem_adapter/`** in the existing scaffold, per the pre-hackathon decision.

---

## 3. Clio READ API surface (what to pull, and why)

The app needs read access to these Clio Manage API v4 resource families for the Sapini matter. Verify exact paths and query parameters against the Clio API v4 docs during implementation — this table is the required *read surface*, not a contract.

| Resource family | Pull | Used for |
|---|---|---|
| Matters (+ custom field values) | Matter metadata, client, status, custom fields | Case header, client picture/name, custom KPIs (coverage, value fields if present) |
| Contacts | Parties, attorneys, medical providers, roles | Who's who; provider identities for provisioning |
| Notes | All matter notes | Core digest input; treatment notes; "is the patient showing up?" |
| Communications | Emails/messages on the matter | Digest input; "when did anyone last talk to the client?" |
| Tasks | Open/completed tasks with due dates | Overdue / coming / waiting-on triage |
| Calendar entries | Deadlines, hearings, depositions | Timeline; "what's coming" |
| Documents (+ file download) | Records, bills, scans → OCR text | Source of truth for citations; injury and billing facts |
| Folders | Document organization | Browsing shared documents |
| Activities | The matter's activity/change feed | Powers "what changed since last visit" |
| Bills | Billing/lien amounts, if exposed in the trial | Lien exposure; case-worth inputs |
| Users | Firm staff list | Attribution in audit trail ("released by …") |

---

## 4. Local data model (entities — fields are illustrative, not schema)

**Mirrored from Clio (read-only copies):** `matter`, `contact`, `note`, `communication`, `task`, `calendar_entry`, `document` (with `extracted_text`), `custom_field_value`, `bill`, `activity`.

**Owned by the app (full CRUD here):**
- `visit` — who opened the matter and when. Powers the "since your last visit" digest.
- `digest` — one row per (matter, content_hash): generated_at, token_usage, cost_usd.
- `key_moment` — ranked moments belonging to a digest: rank, title, one-line why-it-matters, occurred_at.
- `citation` — links a moment/KPI/fact to its source: source_type, source_id, excerpt. **Every surfaced fact must have at least one citation.**
- `kpi_snapshot` — case-worth range, coverage summary, list of assumptions, citations.
- `share_policy` — per provider: boolean toggles per field (status, coverage, case value, bills, open requests, documents) + explicit list of shared document IDs + updated_by/updated_at.
- `share_event` — audit log: policy released, provider viewed the dashboard, document opened (by whom, when).

---

## 5. Access model

### Role A — Firm Administrator (attorneys + firm staff)
- Sees everything: full digest, all KPIs, money lens, all documents, share composer, audit trail.
- **Only this role can provision providers and change what they see.**

### Role B — Medical Provider (restricted)
- Sees **only** what the active `share_policy` for that provider allows. Never sees case strategy, firm spend, other providers' data, or unshared documents.
- Redaction is enforced **server-side** from the share policy. The provider client must never receive unshared fields (no client-side hiding).

### Provisioning flow (must be real, not faked)
1. Admin creates a provider identity (name + practice, picked from Clio contacts).
2. Admin sets the initial share toggles and shared documents.
3. System issues the provider an access token/link.
4. Provider opens the link and sees the scoped view. Any later toggle change by the admin re-renders the provider view immediately.
5. For the demo, a role switcher in the UI is acceptable **in addition to** the real provisioning flow, not instead of it.

---

## 6. Views

### 6a. Existing scaffold views — keep as-is
The current frontend pages (`/jobs`, `/results`, `/review` — ingestion jobs, extraction results, human review of extracted facts) stay untouched. They are the "evidence layer" the new digest views cite into.

### 6b. New views to build

**Administrator views**
- **V1 — Digest home.** Client header (name + picture on open), case phase timeline (incident → treatment → demand → negotiation), and the hero: **"Changed since your last visit"** feed.
- **V2 — Key moments.** The ranked "10 that matter," each expandable to show its citations.
- **V3 — Money.** Case-worth range with assumptions listed, coverage behind the case, firm spend to date, total lien exposure.
- **V4 — Share composer.** Per-provider toggles + document picker + **live "preview as this provider" pane** + release button.
- **V5 — Audit.** Per provider: what was shared, when, and whether anyone in their office opened it.

**Medical provider views**
- **V6 — Case heartbeat.** One glance: is this case alive, when did it last move, coverage behind the case (if shared), open requests from the firm, recently shared documents.

---

## 7. Feature requirements

### F1 — "Changed since your last visit" digest
- **What:** When an admin opens the matter, the top of the digest shows only what's new since *their* last visit, ranked by importance, each with a one-line "why it matters."
- **Why:** Quoted verbatim in the brief; the single highest-value screen; Clio doesn't have it.
- **Must do:** Track per-user visits. On open, diff current matter state against the last visit using the activities feed + new/changed records. Each item links to its source (F3). If nothing changed, say so explicitly — never show a stale "new" badge.

### F2 — Key moments ("the 10 from 300")
- **What:** An importance-ranked list of the moments that define the case (accident, ER visit, surgery, demand letter, deposition, coverage confirmation…). Everything else collapses behind it.
- **Why:** "Out of three hundred entries, show me the ten that matter."
- **Must do:** Ranking must be explainable — each moment carries its rank reason and citations. No hardcoded moment list; it must derive from Sapini's actual records.

### F3 — Click-to-source citations (non-negotiable)
- **What:** Every date, dollar figure, injury, and claim in the UI expands to the exact Clio note, email, or document excerpt it came from.
- **Why:** "If a date is on screen, I need to see where it came from." This is the trust story and the first thing the AI-builder judges will probe.
- **Must do:** Every surfaced fact has ≥1 stored citation with an excerpt. Clicking reveals the excerpt and identifies the source record. Facts without a source must not be shown as facts.

### F4 — Case worth + coverage KPIs
- **What:** The two KPIs attorneys named: estimated case worth and coverage behind the case.
- **Why:** "The two KPIs I care about most."
- **Must do:** Show worth as a **range**, never a single number, with the assumptions listed underneath (bills total, injury severity found, policy limits found). Each assumption cites its source. Label it an estimate. Coverage shows carrier + limits where found in the file, or "not found in file" — never invented.

### F5 — Share composer with live provider preview
- **What:** The admin picks a provider, toggles exactly which fields that provider sees (status, coverage, case value, bills, open requests, documents), picks shared documents, and sees a **live preview of the provider view as that provider** before releasing.
- **Why:** "Let me adjust what the provider sees before I send it." / "I want the treating doctors to see where the case is without handing over my whole file." This is the differentiator — most teams will build two static pages.
- **Must do:** Toggles re-render the preview instantly. Releasing writes a new `share_policy` version + a `share_event`. The provider view must reflect the change on next load.

### F6 — Provider case heartbeat
- **What:** One screen answering: is this case alive, when did it last move, is there coverage behind it (if shared), what does the firm need from my office right now, which documents were recently shared with me.
- **Why:** Every element is a direct provider quote ("Is this case even still alive?" / "Tell me when the case moves" / "What does the firm need from my office right now?").
- **Must do:** "Alive" is derived from recent activity, not a static flag. "Last movement" shows date + plain-language description. Anything not shared with this provider is absent — not shown as redacted, just absent.

### F7 — "What the firm needs from me" (provider requests)
- **What:** A checklist of outstanding items the firm has requested from this provider's office (records, bills, authorizations), derived from tasks/communications.
- **Why:** "What does the firm need from my office right now?"
- **Must do:** Each request cites the task or message it came from. Completing or dismissing a request is app-local state (never writes to Clio).

### F8 — Share audit trail
- **What:** Per provider: what was shared, when it was released, whether anyone in their office opened the dashboard or a document.
- **Why:** "What did we share with this provider, and has anyone in their office opened it?"
- **Must do:** Every release and every provider view/document open appends a `share_event` with timestamp and actor. The admin audit view reads from this log.

### F9 — Digest caching + cost-per-case instrumentation
- **What:** Content-hash caching so an unchanged case is never re-digested, and token/cost logging per digest run.
- **Why:** "Don't digest the whole case with AI again every time someone on my team opens it." The submission form requires approximate cost per case.
- **Must do:** Digest rows store content_hash, token_usage, and cost_usd. The README reports the measured cost to digest Sapini once. Cache hit path must be demonstrable (sync with no changes → no LLM calls).

---

## 8. The 90-second demo script (four beats)

1. **Open as attorney** — "Changed since your last visit" digest on Sapini. (F1)
2. **Click a dollar figure** — it expands to the exact bill/note it came from. (F3)
3. **Open the share composer** — flip a toggle, watch the provider preview update live, hit release. (F5)
4. **Flip to the provider view** — heartbeat, open requests, only what was shared. (F6)

---

## 9. Non-goals (do not build)

- A chat / Q&A interface over the case. The brief explicitly says the solution goes *beyond* asking an AI questions.
- Real notification infrastructure (email/SMS/push). A "movement" view is enough for the demo.
- Write-back to Clio, multi-matter support, real SSO/auth, fancy charts that don't answer a quoted question.
