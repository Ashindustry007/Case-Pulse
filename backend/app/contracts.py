"""API contract (shared, FROZEN). Every request/response body in the app is one of these models.

Rules encoded here:
- F3: a surfaced fact is `Cited[T]` (>= 1 citation, each with a non-empty excerpt) or an explicit `NotFound`.
- List items that are facts carry their own `citations` with the same >= 1 rule.
- Provider-facing models (`ProviderCase`...) have OPTIONAL sections: a section the attorney did not share must be
  ABSENT from the JSON (routes use `response_model_exclude_none=True`), never "redacted".
Frontend types are generated from these via FastAPI's OpenAPI (`make types`).
"""
from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

T = TypeVar("T")

RecordType = Literal[
    "note", "communication", "task", "calendar_entry", "document", "expense", "time_entry",
    "bill", "medical_record", "medical_bill", "damage", "custom_field", "matter_event", "contact",
]
Role = Literal["attorney", "provider"]
ShareField = Literal[
    "status", "coverage", "case_value", "bills", "open_requests", "documents", "adherence", "other_care",
    "case_details",
]
HeartbeatState = Literal["active", "quiet", "dormant", "closed"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------------------------------------------
# Citations (F3)
# ---------------------------------------------------------------------------------------------------------------
class Citation(_Model):
    record_id: str = Field(description='Our record id, e.g. "note:123" or "document:456"')
    source_type: RecordType
    title: str
    author: str | None = None
    date: str | None = Field(default=None, description="ISO date/time of the source item")
    page: int | None = Field(default=None, description="1-based page for document citations")
    char_start: int = Field(ge=0, description="Offset into the source text (record body_text, or the page text when page is set)")
    char_end: int = Field(ge=0)
    excerpt: str = Field(min_length=1, description="The exact cited source text")
    clio_url: str | None = None


class Cited(_Model, Generic[T]):
    value: T
    citations: list[Citation] = Field(min_length=1)


class NotFound(_Model):
    not_found: Literal[True] = True
    label: str = Field(description='What was looked for, e.g. "UM/UIM limits". UI renders "not found in file".')


class CitedSentence(_Model):
    text: str
    citations: list[Citation] = Field(min_length=1)


# ---------------------------------------------------------------------------------------------------------------
# Auth (owner: Dev 2)
# ---------------------------------------------------------------------------------------------------------------
class LoginRequest(_Model):
    email: str
    password: str


class UserOut(_Model):
    id: int
    email: str
    name: str | None = None
    role: Role
    provider_contact_id: int | None = None


class InviteAcceptRequest(_Model):
    password: str = Field(min_length=8)
    name: str | None = None


class OkResponse(_Model):
    ok: bool = True
    message: str | None = None


# ---------------------------------------------------------------------------------------------------------------
# Sync + matters (owner: Dev 1)
# ---------------------------------------------------------------------------------------------------------------
class SyncResult(_Model):
    matter_id: int
    started_at: str
    finished_at: str
    counts: dict[str, int] = Field(description="items pulled per Clio resource")
    new: int
    changed: int
    removed: int


class SyncStatus(_Model):
    connected: bool
    clio_user: str | None = None
    last_synced_at: str | None = None
    matters: int = 0


class MatterSummary(_Model):
    id: int
    display_number: str | None = None
    description: str | None = None
    status: str | None = None
    stage: str | None = None
    client_name: str | None = None
    last_activity_at: str | None = None


class ClientInfo(_Model):
    contact_id: int | None = None
    name: str
    photo_url: str | None = Field(default=None, description="API URL serving the photo, if one was found")
    photo_citation: Citation | None = None
    date_of_birth: Cited[str] | NotFound | None = None
    age: int | None = None
    phone: str | None = None
    email: str | None = None


class StageInfo(_Model):
    current: str | None = None
    stages: list[str] = Field(default_factory=list, description="Ordered stage names for this practice area")
    index: int | None = None


class ClientContact(_Model):
    at: str
    days_ago: int
    channel: str = Field(description="email | call | note | meeting | text | other")
    by: str | None = None
    summary: str | None = None


class DeadlineItem(_Model):
    id: str
    title: str
    kind: Literal["task", "calendar", "sol", "waiting_on"]
    due_at: str | None = None
    status: str | None = None
    assignee: str | None = None
    waiting_on: str | None = None
    overdue: bool = False
    citations: list[Citation] = Field(min_length=1)


class Overview(_Model):
    matter: MatterSummary
    client: ClientInfo
    stage: StageInfo
    date_of_incident: Cited[str] | NotFound
    statute_of_limitations: Cited[str] | NotFound
    firm_spend: Cited[float] | NotFound
    medical_specials: Cited[float] | NotFound
    next_deadline: DeadlineItem | None = None
    last_client_contact: Cited[ClientContact] | NotFound
    last_synced_at: str | None = None
    last_digested_at: str | None = None


class TimelineItem(_Model):
    record_id: str
    type: RecordType
    title: str
    occurred_at: str | None = None
    author: str | None = None
    one_liner: str | None = None
    category: str | None = None
    importance: int | None = None
    citations: list[Citation] = Field(min_length=1)


class Timeline(_Model):
    items: list[TimelineItem]
    total: int


class Deadlines(_Model):
    overdue: list[DeadlineItem]
    upcoming: list[DeadlineItem]
    waiting_on: list[DeadlineItem]


class CostCategory(_Model):
    category: str
    amount: float
    count: int
    citations: list[Citation] = Field(min_length=1)


class MonthAmount(_Model):
    month: str  # YYYY-MM
    amount: float


class Costs(_Model):
    total: Cited[float] | NotFound
    by_category: list[CostCategory]
    monthly: list[MonthAmount]


class Visit(_Model):
    date: str
    description: str | None = None
    citations: list[Citation] = Field(min_length=1)


class ProviderSummary(_Model):
    contact_id: int
    name: str
    email: str | None = None
    phone: str | None = None
    relationship: str | None = None
    billed: Cited[float] | NotFound
    balance: Cited[float] | NotFound
    lien: bool = False
    visits: list[Visit] = Field(default_factory=list)
    first_visit: str | None = None
    last_visit: str | None = None
    current_gap_days: int | None = None
    longest_gap_days: int | None = None
    open_requests: int = 0


class Providers(_Model):
    providers: list[ProviderSummary]


class SourceRecord(_Model):
    record_id: str
    type: RecordType
    title: str
    author: str | None = None
    occurred_at: str | None = None
    body_text: str = Field(description="Full text; citation offsets without a page index into this")
    participants: list[dict] = Field(default_factory=list)
    page_count: int | None = Field(default=None, description="Set for documents; fetch pages separately")
    clio_url: str | None = None
    meta: dict = Field(default_factory=dict)


class DocumentPage(_Model):
    document_id: str
    page_no: int
    page_count: int
    text: str
    method: Literal["text_layer", "ocr", "none", "pending"]
    image_url: str | None = None


# ---------------------------------------------------------------------------------------------------------------
# F1 — changed since last visit
# ---------------------------------------------------------------------------------------------------------------
class VisitResponse(_Model):
    visit_id: int
    visited_at: str
    previous_visit_at: str | None = Field(default=None, description="Baseline for /changes; null on first visit")
    first_visit: bool
    synced: bool = Field(description="True if a fresh incremental Clio sync ran before this response")


class ChangeItem(_Model):
    record_id: str
    change: Literal["new", "changed", "removed"]
    type: RecordType
    title: str
    occurred_at: str | None = None
    importance: int | None = None
    why_it_matters: str | None = None
    citations: list[Citation] = Field(min_length=1)


class LastActivity(_Model):
    at: str
    description: str
    citations: list[Citation] = Field(min_length=1)


class Changes(_Model):
    since: str | None
    first_visit: bool
    items: list[ChangeItem]
    empty_message: str | None = Field(default=None, description='Set when nothing changed: "Nothing has changed since..."')
    last_activity: LastActivity | None = None


class Delta(_Model):
    since: str | None
    summary: list[CitedSentence]
    cached: bool


# ---------------------------------------------------------------------------------------------------------------
# Brief: F2 key moments, F4 worth + coverage, injuries, story
# ---------------------------------------------------------------------------------------------------------------
class KeyMoment(_Model):
    rank: int
    date: str | None = None
    title: str
    importance: int
    rank_reason: str
    citations: list[Citation] = Field(min_length=1)


class Injury(_Model):
    name: str
    body_region: str | None = None
    severity_tier: Literal["soft_tissue", "objective", "surgical"] | None = None
    primary: bool = False
    description: str | None = None
    citations: list[Citation] = Field(min_length=1)


class Assumption(_Model):
    label: str = Field(description='"Bills total" | "Injury severity" | "Policy limits" | ...')
    text: str
    not_found: bool = False
    citations: list[Citation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cited_unless_not_found(self) -> "Assumption":
        if not self.not_found and not self.citations:
            raise ValueError("an assumption must cite a source unless it is not_found")
        return self


class WorthEstimate(_Model):
    label: Literal["Estimate"] = "Estimate"
    low: float
    high: float
    currency: str = "USD"
    assumptions: list[Assumption] = Field(min_length=1)
    cap_note: str | None = None
    method: str = Field(description="Plain-language description of the deterministic method")


class Coverage(_Model):
    carrier: Cited[str] | NotFound
    bi_per_person: Cited[str] | NotFound
    bi_per_accident: Cited[str] | NotFound
    um_uim: Cited[str] | NotFound
    medpay: Cited[str] | NotFound
    confirmed: bool = Field(description="True if any liability coverage fact was found")


class Brief(_Model):
    matter_id: int
    story: list[CitedSentence]
    key_moments: list[KeyMoment]
    total_records: int
    injuries: list[Injury]
    worth: WorthEstimate | NotFound
    coverage: Coverage
    waiting_on: list[DeadlineItem]
    last_client_contact: Cited[ClientContact] | NotFound
    digested_at: str | None = None
    cost_usd: float = 0.0
    stale: bool = Field(description="True if records changed since the last digest run")


class SuggestedQuestions(_Model):
    questions: list[str]


# ---------------------------------------------------------------------------------------------------------------
# Ask (RAG) + locate + provider draft
# ---------------------------------------------------------------------------------------------------------------
class AskTurn(_Model):
    question: str
    answer_text: str


class AskRequest(_Model):
    question: str = Field(min_length=1)
    history: list[AskTurn] = Field(default_factory=list)


class AnswerSegment(_Model):
    """SSE event "segment". Uncited connective text has citations == []."""
    id: str
    text: str
    citations: list[Citation] = Field(default_factory=list)


class Answer(_Model):
    """SSE event "done" carries {followups, cost_usd}; full Answer is also logged to qa_log."""
    segments: list[AnswerSegment]
    followups: list[str] = Field(default_factory=list)
    cost_usd: float = 0.0


class LocateRequest(_Model):
    text: str = Field(min_length=3)


class LocateResult(_Model):
    supported: bool
    citations: list[Citation]
    explanation: str


class ProviderDraftRequest(_Model):
    provider_contact_id: int
    fields: list[ShareField]


class DraftFlag(_Model):
    text: str
    reason: str


class ProviderDraft(_Model):
    draft: str
    flags: list[DraftFlag]


# ---------------------------------------------------------------------------------------------------------------
# F9 + F10 — digestion runs and AI cost
# ---------------------------------------------------------------------------------------------------------------
class DigestRun(_Model):
    id: int
    matter_id: int
    trigger: str
    started_at: str
    finished_at: str | None = None
    records_seen: int
    records_changed: int
    llm_calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cache_hit: bool
    stages: dict = Field(default_factory=dict)


class PurposeCost(_Model):
    key: str
    usd: float
    calls: int


class DayCost(_Model):
    date: str
    usd: float


class AiRun(_Model):
    at: str
    user: str | None = None
    purpose: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cache_hit: bool = False


class AiCostReport(_Model):
    matter_id: int | None
    total_usd: float
    one_time_usd: float
    ongoing_usd: float
    ask_count: int
    avg_ask_usd: float
    cache_savings_usd: float
    by_purpose: list[PurposeCost]
    by_model: list[PurposeCost]
    series: list[DayCost]
    budget_usd: float | None = None
    budget_pct: float | None = None
    runs: list[AiRun]


class MatterCost(_Model):
    matter_id: int
    display_number: str | None = None
    description: str | None = None
    total_usd: float


class FirmCostReport(_Model):
    matters: list[MatterCost]
    series: list[DayCost]
    total_usd: float


# ---------------------------------------------------------------------------------------------------------------
# Sharing (owner: Dev 2) — F5..F8
# ---------------------------------------------------------------------------------------------------------------
class StageShare(_Model):
    current: str | None = None
    stages: list[str] = Field(default_factory=list)
    index: int | None = None


class Movement(_Model):
    date: str
    text: str


class Heartbeat(_Model):
    state: HeartbeatState
    last_activity_at: str | None = None
    last_movement: Movement | None = None
    stage: StageShare | None = None
    recent_movement: list[Movement] = Field(default_factory=list)


class CoverageShare(_Model):
    confirmed: bool
    carrier: str | None = None
    limits_text: str | None = Field(default=None, description='Only when coverage_detail == "limits"')


class CaseValueShare(_Model):
    label: Literal["Estimate"] = "Estimate"
    low: float
    high: float


class BillLine(_Model):
    date: str | None = None
    amount: float
    description: str | None = None


class ProviderBills(_Model):
    billed: float
    balance: float | None = None
    lien: bool = False
    items: list[BillLine] = Field(default_factory=list)


class ProviderRequest(_Model):
    id: str
    kind: Literal["records", "bills", "authorization", "other"]
    description: str
    requested_at: str | None = None
    channel: str | None = None
    state: Literal["open", "completed", "dismissed"] = "open"
    provider_contact_id: int | None = None
    citations: list[Citation] = Field(
        default_factory=list,
        description="Always populated for attorneys; for providers only if the source was addressed to them",
    )


class SharedDocument(_Model):
    id: str = Field(description="records.id of the document")
    title: str
    shared_at: str | None = None
    page_count: int | None = None
    category: str | None = Field(default=None, description='e.g. "Medical records", "Medical bills", "Pleadings"')


class CaseDetailOption(_Model):
    """One case detail (a Clio custom field of the matter) the attorney may choose to share (composer only)."""
    id: str = Field(description="records.id of the custom_field record")
    label: str
    value: str
    confidential: bool = Field(description="Strategy/valuation/opinion content — warn before sharing")
    recommended: bool = Field(description="Safe, useful default for a treating provider")


class CaseDetail(_Model):
    """A case detail as the provider sees it (label + value only)."""
    label: str
    value: str


class Adherence(_Model):
    visits: list[str] = Field(description="ISO dates of recorded visits")
    gaps: list[dict] = Field(default_factory=list, description="[{from, to, days}] gaps over the threshold")
    current_gap_days: int | None = None


class OtherCare(_Model):
    provider_name: str
    first_visit: str | None = None
    last_visit: str | None = None


class ProviderCase(_Model):
    """Provider view. Sections not granted by the latest policy are None and MUST be excluded from JSON."""
    grant_id: int
    policy_version: int
    patient_display: str
    firm_name: str
    shared_by: str | None = None
    updated_at: str | None = None
    heartbeat: Heartbeat | None = None
    status_note: str | None = None
    coverage: CoverageShare | None = None
    case_value: CaseValueShare | None = None
    bills: ProviderBills | None = None
    requests: list[ProviderRequest] | None = None
    documents: list[SharedDocument] | None = None
    adherence: Adherence | None = None
    other_care: list[OtherCare] | None = None
    case_details: list[CaseDetail] | None = None


class ProviderCaseSummary(_Model):
    grant_id: int
    patient_display: str
    firm_name: str
    state: HeartbeatState | None = None
    last_movement_at: str | None = None
    open_requests: int = 0


class ProviderIdentity(_Model):
    contact_id: int
    name: str
    email: str | None = None


class ShareCandidates(_Model):
    """Everything this provider COULD see, already scoped to them. The composer preview filters it client-side."""
    provider: ProviderIdentity
    case: ProviderCase = Field(description="All sections populated (coverage per coverage_variants)")
    coverage_variants: dict[str, CoverageShare] = Field(description='{"confirmed": ..., "limits": ...}')
    available_documents: list[SharedDocument]
    case_detail_options: list[CaseDetailOption] = Field(default_factory=list)


class CreateGrantRequest(_Model):
    matter_id: int
    provider_contact_id: int
    email: str


class Grant(_Model):
    id: int
    matter_id: int
    provider_contact_id: int
    provider_name: str | None = None
    email: str
    provider_user_id: int | None = None
    latest_version: int | None = None
    released_at: str | None = None
    revoked_at: str | None = None
    last_viewed_at: str | None = None
    view_count: int = 0


class ReleaseRequest(_Model):
    fields: list[ShareField]
    document_ids: list[str] = Field(default_factory=list)
    case_fields: list[str] = Field(default_factory=list,
                                   description='CaseDetailOption ids to share (used when "case_details" is in fields)')
    coverage_detail: Literal["confirmed", "limits"] = "confirmed"
    status_note: str | None = None


class SharePolicy(_Model):
    grant_id: int
    version: int
    fields: list[ShareField]
    document_ids: list[str]
    case_fields: list[str] = Field(default_factory=list)
    coverage_detail: Literal["confirmed", "limits"]
    status_note: str | None = None
    released_by: str | None = None
    released_at: str


class ReleaseResult(_Model):
    policy: SharePolicy
    invite_url: str | None = Field(default=None, description="Set when an invite was created (also printed to the server console)")


class ShareEvent(_Model):
    id: int
    grant_id: int
    policy_version: int | None = None
    event: Literal["released", "viewed", "document_opened", "request_completed", "request_dismissed",
                   "revoked", "invite_sent", "invite_accepted"]
    actor_email: str | None = None
    at: str
    meta: dict = Field(default_factory=dict)


class PolicyVersionDiff(_Model):
    policy: SharePolicy
    added: list[str]
    removed: list[str]


class ShareAudit(_Model):
    grant: Grant
    versions: list[PolicyVersionDiff]
    events: list[ShareEvent]
