"""Generate fixtures/*.json for Phase 0 stub endpoints. Data is SYNTHETIC and generic (no real case content).
Every fixture is built through the contract models, so it is valid by construction.
Deleted (with fixtures/ and backend/app/stubs.py) by the 14:45 freeze once all endpoints are real.

    uv run python scripts/gen_fixtures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app import contracts as C  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "fixtures"
MATTER = 1001


def cite(rid: str, typ: str, title: str, excerpt: str, *, page: int | None = None, date: str | None = "2025-03-14",
         author: str | None = "Paralegal") -> C.Citation:
    return C.Citation(record_id=rid, source_type=typ, title=title, author=author, date=date, page=page,
                      char_start=0, char_end=len(excerpt), excerpt=excerpt)


N1 = cite("note:1", "note", "Intake call", "Client was rear-ended at a red light on 03/14/2025 and taken to the ER.")
N2 = cite("note:2", "note", "Call with client", "Spoke with client; still in PT twice weekly, pain 6/10.",
          date="2026-09-09")
D_MRI = cite("document:10", "document", "MRI Report - Lumbar.pdf",
             "Impression: L4-L5 posterior disc herniation with left neural foraminal narrowing.", page=3,
             date="2025-04-02", author=None)
D_DEC = cite("document:11", "document", "Declarations Page.pdf",
             "Bodily Injury Liability: $100,000 each person / $300,000 each accident.", page=1, date="2025-06-02",
             author=None)
E_ADJ = cite("communication:20", "communication", "RE: Claim 55-1234 — IME request",
             "We are requesting an independent medical examination before evaluating the demand.", date="2026-09-29",
             author="Adjuster")
B_ORTHO = cite("medical_bill:30", "medical_bill", "Medical bill · Northside Orthopedics",
               "Medical bill · Northside Orthopedics · $22,140.00 · 2025-05-02", date="2025-05-02", author=None)
B_PT = cite("medical_bill:31", "medical_bill", "Medical bill · Harbor Physical Therapy",
            "Medical bill · Harbor Physical Therapy · $9,400.00 · 2025-08-30", date="2025-08-30", author=None)
T_REC = cite("task:40", "task", "Request PT records 06/01–09/01",
             "Task: Request PT records 06/01–09/01 from Harbor Physical Therapy · due 2026-09-20", date="2026-09-20")
X_EXP = cite("expense:50", "expense", "Expense · Medical records fee", "Expense · Medical records fee · $85.00",
             date="2025-07-01")
CF_SOL = cite("custom_field:60", "custom_field", "Custom field · Statute of Limitations",
              "Statute of Limitations: 2027-03-14", date=None, author=None)
P_PHOTO = cite("document:12", "document", "client_photo.jpg", "Client photo (image document)", date=None, author=None)

STAGES = ["Intake", "Treatment", "Demand", "Negotiation", "Litigation", "Settlement"]


def dump(name: str, obj) -> None:
    data = obj.model_dump(mode="json") if hasattr(obj, "model_dump") else [o.model_dump(mode="json") for o in obj]
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    summary = C.MatterSummary(id=MATTER, display_number="00042-Rivera", description="Rivera v. Example Trucking",
                              status="open", stage="Treatment", client_name="Jordan Rivera",
                              last_activity_at="2026-09-29T16:02:00Z")
    dump("matters", [summary])
    contact = C.ClientContact(at="2026-09-09T15:30:00Z", days_ago=23, channel="call", by="Paralegal",
                              summary="Status check on treatment")
    dl_overdue = C.DeadlineItem(id="task:40", title="Request PT records 06/01–09/01", kind="task",
                                due_at="2026-09-20", status="pending", assignee="Paralegal", overdue=True,
                                citations=[T_REC])
    dl_next = C.DeadlineItem(id="calendar_entry:70", title="IME appointment", kind="calendar",
                             due_at="2026-10-15T09:00:00", citations=[E_ADJ])
    dl_sol = C.DeadlineItem(id="sol", title="Statute of limitations", kind="sol", due_at="2027-03-14",
                            citations=[CF_SOL])
    dl_wait = C.DeadlineItem(id="waiting:1", title="PT records from Harbor Physical Therapy", kind="waiting_on",
                             waiting_on="Harbor Physical Therapy", citations=[T_REC])
    dump("overview", C.Overview(
        matter=summary,
        client=C.ClientInfo(contact_id=500, name="Jordan Rivera", photo_url="/api/documents/document:12/file",
                            photo_citation=P_PHOTO, date_of_birth=C.NotFound(label="Date of birth"),
                            phone="(555) 010-0000", email="client@example.com"),
        stage=C.StageInfo(current="Treatment", stages=STAGES, index=1),
        date_of_incident=C.Cited[str](value="2025-03-14", citations=[N1]),
        statute_of_limitations=C.Cited[str](value="2027-03-14", citations=[CF_SOL]),
        firm_spend=C.Cited[float](value=6430.0, citations=[X_EXP]),
        medical_specials=C.Cited[float](value=31540.0, citations=[B_ORTHO, B_PT]),
        next_deadline=dl_next,
        last_client_contact=C.Cited[C.ClientContact](value=contact, citations=[N2]),
        last_synced_at="2026-10-02T17:41:00Z", last_digested_at="2026-10-02T17:42:00Z"))
    dump("timeline", C.Timeline(total=4, items=[
        C.TimelineItem(record_id="note:1", type="note", title="Intake call", occurred_at="2025-03-14",
                       author="Paralegal", one_liner="Rear-end collision; ER visit same day", category="liability",
                       importance=10, citations=[N1]),
        C.TimelineItem(record_id="document:10", type="document", title="MRI Report - Lumbar.pdf",
                       occurred_at="2025-04-02", one_liner="MRI confirms L4-L5 herniation", category="medical",
                       importance=9, citations=[D_MRI]),
        C.TimelineItem(record_id="document:11", type="document", title="Declarations Page.pdf",
                       occurred_at="2025-06-02", one_liner="BI limits 100k/300k", category="coverage",
                       importance=9, citations=[D_DEC]),
        C.TimelineItem(record_id="communication:20", type="communication", title="RE: Claim — IME request",
                       occurred_at="2026-09-29", author="Adjuster", one_liner="Adjuster requests IME",
                       category="negotiation", importance=8, citations=[E_ADJ]),
    ]))
    dump("deadlines", C.Deadlines(overdue=[dl_overdue], upcoming=[dl_next, dl_sol], waiting_on=[dl_wait]))
    dump("costs", C.Costs(total=C.Cited[float](value=6430.0, citations=[X_EXP]),
                          by_category=[C.CostCategory(category="Medical records", amount=85.0, count=1,
                                                      citations=[X_EXP])],
                          monthly=[C.MonthAmount(month="2025-07", amount=85.0),
                                   C.MonthAmount(month="2026-09", amount=6345.0)]))
    dump("providers", C.Providers(providers=[
        C.ProviderSummary(contact_id=600, name="Northside Orthopedics", email="records@northside.example",
                          relationship="Treating Physician",
                          billed=C.Cited[float](value=22140.0, citations=[B_ORTHO]),
                          balance=C.Cited[float](value=18000.0, citations=[B_ORTHO]), lien=True,
                          visits=[C.Visit(date="2025-05-02", citations=[B_ORTHO])],
                          first_visit="2025-05-02", last_visit="2026-09-12", current_gap_days=20,
                          longest_gap_days=41, open_requests=1),
        C.ProviderSummary(contact_id=601, name="Harbor Physical Therapy", relationship="Physical Therapist",
                          billed=C.Cited[float](value=9400.0, citations=[B_PT]),
                          balance=C.NotFound(label="Balance"), lien=True,
                          visits=[C.Visit(date="2025-08-30", citations=[B_PT])],
                          first_visit="2025-04-10", last_visit="2025-08-30", open_requests=1),
    ]))
    dump("record", C.SourceRecord(record_id="note:1", type="note", title="Intake call", author="Paralegal",
                                  occurred_at="2025-03-14", body_text=N1.excerpt + " Client reports neck and low back pain."))
    dump("document_page", C.DocumentPage(document_id="document:10", page_no=3, page_count=5, text=D_MRI.excerpt,
                                         method="ocr", image_url=None))
    dump("visit", C.VisitResponse(visit_id=1, visited_at="2026-10-02T17:45:00Z",
                                  previous_visit_at="2026-09-28T17:14:00Z", first_visit=False, synced=True))
    dump("changes", C.Changes(since="2026-09-28T17:14:00Z", first_visit=False, items=[
        C.ChangeItem(record_id="communication:20", change="new", type="communication", title="RE: Claim — IME request",
                     occurred_at="2026-09-29", importance=9, why_it_matters="IME request delays demand timing",
                     citations=[E_ADJ]),
    ], last_activity=C.LastActivity(at="2026-09-29", description="Email from adjuster", citations=[E_ADJ])))
    dump("delta", C.Delta(since="2026-09-28T17:14:00Z", cached=True, summary=[
        C.CitedSentence(text="The adjuster requested an IME before evaluating the demand.", citations=[E_ADJ])]))
    worth = C.WorthEstimate(low=63080.0, high=126160.0, cap_note="Recovery may be capped by available coverage of $100,000.",
                            method="Medical specials × multiplier band for the injury severity tier (value_model.yaml).",
                            assumptions=[
                                C.Assumption(label="Bills total", text="$31,540 in medical bills",
                                             citations=[B_ORTHO, B_PT]),
                                C.Assumption(label="Injury severity", text="Objective injury (disc herniation)",
                                             citations=[D_MRI]),
                                C.Assumption(label="Policy limits", text="BI $100,000 per person", citations=[D_DEC]),
                            ])
    coverage = C.Coverage(carrier=C.Cited[str](value="Example Mutual Insurance", citations=[D_DEC]),
                          bi_per_person=C.Cited[str](value="$100,000", citations=[D_DEC]),
                          bi_per_accident=C.Cited[str](value="$300,000", citations=[D_DEC]),
                          um_uim=C.NotFound(label="UM/UIM limits"), medpay=C.NotFound(label="MedPay"),
                          confirmed=True)
    dump("brief", C.Brief(
        matter_id=MATTER, total_records=312,
        story=[C.CitedSentence(text="Client was rear-ended on 03/14/2025 and treated in the ER the same day.",
                               citations=[N1]),
               C.CitedSentence(text="An MRI confirmed an L4-L5 disc herniation.", citations=[D_MRI]),
               C.CitedSentence(text="The carrier disclosed BI limits of $100k/$300k.", citations=[D_DEC])],
        key_moments=[C.KeyMoment(rank=1, date="2025-03-14", title="Accident and ER visit", importance=10,
                                 rank_reason="Establishes liability facts and date of incident", citations=[N1]),
                     C.KeyMoment(rank=2, date="2025-04-02", title="MRI: L4-L5 herniation", importance=9,
                                 rank_reason="Objective injury drives case value", citations=[D_MRI])],
        injuries=[C.Injury(name="L4-L5 disc herniation", body_region="lumbar spine", severity_tier="objective",
                           primary=True, citations=[D_MRI])],
        worth=worth, coverage=coverage, waiting_on=[dl_wait],
        last_client_contact=C.Cited[C.ClientContact](value=contact, citations=[N2]),
        digested_at="2026-10-02T17:42:00Z", cost_usd=2.31, stale=False))
    dump("suggested_questions", C.SuggestedQuestions(questions=[
        "What are the client's primary injuries?", "What coverage is behind this case?",
        "What is blocking the demand?", "When did we last talk to the client?"]))
    dump("answer", C.Answer(segments=[
        C.AnswerSegment(id="s1", text="The MRI confirms an L4-L5 posterior disc herniation", citations=[D_MRI]),
        C.AnswerSegment(id="s2", text=", which is the primary injury in the file.", citations=[]),
    ], followups=["What treatment has the client received for the herniation?"], cost_usd=0.08))
    dump("locate", C.LocateResult(supported=True, citations=[D_MRI],
                                  explanation="The MRI report impression states this finding."))
    dump("provider_draft", C.ProviderDraft(
        draft="Treatment is ongoing and the case is active. We have requested your records for 06/01–09/01.",
        flags=[]))
    run = C.DigestRun(id=1, matter_id=MATTER, trigger="manual", started_at="2026-10-02T17:40:00Z",
                      finished_at="2026-10-02T17:42:00Z", records_seen=312, records_changed=0, llm_calls=0,
                      input_tokens=0, output_tokens=0, cost_usd=0.0, cache_hit=True,
                      stages={"digest": {"items": 312, "llm_calls": 0, "skipped": 312}})
    dump("digest_run", run)
    dump("digest_runs", [run])
    dump("sync_result", C.SyncResult(matter_id=MATTER, started_at="2026-10-02T17:40:00Z",
                                     finished_at="2026-10-02T17:41:00Z",
                                     counts={"notes": 120, "communications": 90, "tasks": 40, "documents": 35},
                                     new=0, changed=0, removed=0))
    dump("sync_status", C.SyncStatus(connected=True, clio_user="Firm Attorney",
                                     last_synced_at="2026-10-02T17:41:00Z", matters=1))
    dump("ai_costs", C.AiCostReport(
        matter_id=MATTER, total_usd=2.31, one_time_usd=1.96, ongoing_usd=0.35, ask_count=4, avg_ask_usd=0.0875,
        cache_savings_usd=5.70,
        by_purpose=[C.PurposeCost(key="ocr", usd=0.82, calls=40), C.PurposeCost(key="digest", usd=0.61, calls=22),
                    C.PurposeCost(key="extract", usd=0.53, calls=6), C.PurposeCost(key="ask", usd=0.35, calls=4)],
        by_model=[C.PurposeCost(key="claude-haiku-4-5", usd=1.43, calls=62),
                  C.PurposeCost(key="claude-opus-5-5", usd=0.88, calls=10)],
        series=[C.DayCost(date="2026-10-02", usd=2.31)], budget_usd=5.0, budget_pct=46.2,
        runs=[C.AiRun(at="2026-10-02T17:42:00Z", user="Firm Attorney", purpose="ask", model="claude-opus-5-5",
                      input_tokens=18200, output_tokens=700, cost_usd=0.087)]))
    dump("firm_costs", C.FirmCostReport(total_usd=2.31, series=[C.DayCost(date="2026-10-02", usd=2.31)],
                                        matters=[C.MatterCost(matter_id=MATTER, display_number="00042-Rivera",
                                                              description="Rivera v. Example Trucking",
                                                              total_usd=2.31)]))

    # ---- Dev 2 (sharing) fixtures ----
    req = C.ProviderRequest(id="req:1", kind="records", description="Records for visits 06/01–09/01",
                            requested_at="2026-09-20", channel="task", provider_contact_id=600, citations=[T_REC])
    heartbeat = C.Heartbeat(state="active", last_activity_at="2026-09-29",
                            last_movement=C.Movement(date="2026-09-29", text="Case moved to Demand stage"),
                            stage=C.StageShare(current="Demand", stages=STAGES, index=2),
                            recent_movement=[C.Movement(date="2026-09-29", text="Case moved to Demand stage"),
                                             C.Movement(date="2026-09-12", text="ER records received")])
    full_case = C.ProviderCase(
        grant_id=1, policy_version=2, patient_display="J. R.", firm_name="Your Firm", shared_by="Firm Attorney",
        updated_at="2026-10-01T16:02:00Z", heartbeat=heartbeat,
        status_note="Treatment is ongoing; we need your records for 06/01–09/01.",
        coverage=C.CoverageShare(confirmed=True), case_value=C.CaseValueShare(low=63080.0, high=126160.0),
        bills=C.ProviderBills(billed=22140.0, balance=18000.0, lien=True,
                              items=[C.BillLine(date="2025-05-02", amount=22140.0, description="Orthopedic care")]),
        requests=[req], documents=[C.SharedDocument(id="document:10", title="MRI Report - Lumbar.pdf",
                                                    shared_at="2026-10-01", page_count=5)],
        adherence=C.Adherence(visits=["2025-05-02", "2025-06-10", "2026-09-12"],
                              gaps=[{"from": "2025-06-10", "to": "2025-07-21", "days": 41}], current_gap_days=20),
        other_care=[C.OtherCare(provider_name="Harbor Physical Therapy", first_visit="2025-04-10",
                                last_visit="2025-08-30")])
    dump("share_candidates", C.ShareCandidates(
        provider=C.ProviderIdentity(contact_id=600, name="Northside Orthopedics", email="records@northside.example"),
        case=full_case,
        coverage_variants={"confirmed": C.CoverageShare(confirmed=True),
                           "limits": C.CoverageShare(confirmed=True, carrier="Example Mutual Insurance",
                                                     limits_text="BI $100,000 / $300,000")},
        available_documents=full_case.documents or []))
    grant = C.Grant(id=1, matter_id=MATTER, provider_contact_id=600, provider_name="Northside Orthopedics",
                    email="records@northside.example", provider_user_id=2, latest_version=2,
                    released_at="2026-10-01T16:02:00Z", last_viewed_at="2026-10-01T16:14:00Z",
                    view_count=2)
    dump("grant", grant)
    dump("grants", [grant])
    policy = C.SharePolicy(grant_id=1, version=2, fields=["status", "coverage", "bills", "open_requests", "documents"],
                           document_ids=["document:10"], coverage_detail="confirmed",
                           status_note=full_case.status_note, released_by="Firm Attorney",
                           released_at="2026-10-01T16:02:00Z")
    dump("release_result", C.ReleaseResult(policy=policy, invite_url=None))
    dump("share_audit", C.ShareAudit(grant=grant, versions=[C.PolicyVersionDiff(policy=policy, added=["coverage"],
                                                                                   removed=[])],
                                     events=[C.ShareEvent(id=1, grant_id=1, policy_version=2, event="released",
                                                          actor_email="attorney@firm.test",
                                                          at="2026-10-01T16:02:00Z"),
                                             C.ShareEvent(id=2, grant_id=1, policy_version=2, event="viewed",
                                                          actor_email="records@northside.example",
                                                          at="2026-10-01T16:14:00Z")]))
    shared_case = full_case.model_copy(update={"case_value": None, "adherence": None, "other_care": None})
    dump("provider_case", shared_case)
    dump("provider_cases", [C.ProviderCaseSummary(grant_id=1, patient_display="J. R.", firm_name="Your Firm",
                                                  state="active", last_movement_at="2026-09-29", open_requests=1)])
    print(f"wrote {len(list(OUT.glob('*.json')))} fixtures → {OUT}")


if __name__ == "__main__":
    main()
