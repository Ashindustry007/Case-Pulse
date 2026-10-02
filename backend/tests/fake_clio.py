"""Offline stand-in for ClioClient (TESTS ONLY). Serves a small SYNTHETIC personal-injury matter in Clio API v4 shape,
including a PDF whose page 2 is image-only (a "scan") so the OCR path is exercised. Never imported by app code."""
from __future__ import annotations

import copy
import io
from typing import Any, Iterator

MATTER_ID = 9001


def _pdf_bytes() -> bytes:
    import pymupdf

    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "EMERGENCY DEPARTMENT REPORT\nDate of service: 2025-03-14\n"
                             "Chief complaint: neck and low back pain after rear-end motor vehicle collision.\n"
                             "Assessment: cervical strain. Lumbar strain.", fontsize=11)
    # page 2: an image of text only (no text layer) — simulates a scanned page
    img_doc = pymupdf.open()
    ip = img_doc.new_page(width=400, height=200)
    ip.insert_text((20, 60), "MRI LUMBAR SPINE 2025-04-02\nImpression: L4-L5 disc herniation.", fontsize=12)
    pix = ip.get_pixmap(dpi=100)
    p2 = doc.new_page()
    p2.insert_image(p2.rect, stream=pix.tobytes("png"))
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


class FakeClio:
    def __init__(self) -> None:
        self.requests_made = 0
        self.data = self._dataset()

    # Mutators used by tests to simulate changes in Clio between syncs
    def edit_note(self, note_id: int, detail: str) -> None:
        for n in self.data["/notes.json"]:
            if n["id"] == note_id:
                n["detail"] = detail
                n["updated_at"] = "2026-10-02T18:00:00Z"

    def set_stage(self, name: str) -> None:
        self.data["matter"]["matter_stage"] = {"id": 3, "name": name}

    def request(self, method: str, path: str, params: dict | None = None):
        from backend.app.clio.client import ReadOnlyViolation

        if method.upper() != "GET":
            raise ReadOnlyViolation(method)
        raise NotImplementedError

    def get(self, path: str, *, fields: str | None = None, **params: Any) -> dict:
        self.requests_made += 1
        if path == f"/matters/{MATTER_ID}.json":
            return {"data": copy.deepcopy(self.data["matter"])}
        if path.startswith("/contacts/"):
            cid = int(path.split("/")[2].split(".")[0])
            return {"data": copy.deepcopy(self.data["contacts"][cid])}
        if path == "/users/who_am_i.json":
            return {"data": {"id": 1, "name": "Test Attorney", "email": "a@firm.test"}}
        raise KeyError(path)

    def paginate(self, path: str, *, fields: str | None = None, limit: int = 200, **params: Any) -> Iterator[dict]:
        self.requests_made += 1
        if path == "/matters.json":
            m = self.data["matter"]
            yield {"id": m["id"], "display_number": m["display_number"], "description": m["description"],
                   "status": m["status"], "client": m["client"]}
            return
        yield from copy.deepcopy(self.data.get(path, []))

    def download(self, document_id: int) -> tuple[bytes, str | None]:
        self.requests_made += 1
        return self.data["files"][document_id]

    # ------------------------------------------------------------------------------------------------------------
    @staticmethod
    def _dataset() -> dict:
        client = {"id": 501, "name": "Alex Sample", "type": "Person", "date_of_birth": "1990-06-01",
                  "primary_email_address": "alex@example.com", "primary_phone_number": "555-0100",
                  "custom_field_values": []}
        ortho = {"id": 601, "name": "Lakeside Orthopedics", "type": "Company",
                 "primary_email_address": "records@lakeside.example", "custom_field_values": []}
        pt = {"id": 602, "name": "Bayview Physical Therapy", "type": "Company",
              "primary_email_address": "front@bayview.example", "custom_field_values": []}
        adjuster = {"id": 701, "name": "Pat Adjuster", "type": "Person", "title": "Claims Adjuster",
                    "company": {"id": 9, "name": "Sample Mutual Insurance"},
                    "primary_email_address": "pat@samplemutual.example", "custom_field_values": []}
        matter = {
            "id": MATTER_ID, "display_number": "00099-Sample", "description": "Sample v. Delivery Co",
            "status": "open", "open_date": "2025-03-20", "client": {"id": 501, "name": "Alex Sample", "type": "Person"},
            "practice_area": {"id": 1, "name": "Personal Injury"}, "matter_stage": {"id": 2, "name": "Treatment"},
            "relationships": [
                {"id": 1, "description": "Treating Physician", "contact": {"id": 601, "name": "Lakeside Orthopedics"}},
                {"id": 2, "description": "Physical Therapist", "contact": {"id": 602, "name": "Bayview Physical Therapy"}},
                {"id": 3, "description": "Insurance Adjuster", "contact": {"id": 701, "name": "Pat Adjuster"}},
            ],
            "custom_field_values": [
                {"id": "date-1", "field_name": "Date of Incident", "field_type": "date", "value": "2025-03-14"},
                {"id": "date-2", "field_name": "Statute of Limitations", "field_type": "date", "value": "2027-03-14"},
                {"id": "currency-3", "field_name": "BI Policy Limit (per person)", "field_type": "currency",
                 "value": 100000},
            ],
        }
        notes = [
            {"id": 1, "subject": "Intake call", "date": "2025-03-20", "author": {"id": 1, "name": "Paralegal One"},
             "detail": "Client was rear-ended at a red light on 03/14/2025 by a delivery van and taken to the ER. "
                       "Client reports neck and low back pain."},
            {"id": 2, "subject": "Call with client", "date": "2026-09-09", "author": {"id": 1, "name": "Paralegal One"},
             "detail": "Spoke with client by phone. Still attending PT twice weekly; pain 6/10. Missed one PT visit in August."},
            {"id": 3, "subject": "Strategy", "date": "2026-09-15", "author": {"id": 2, "name": "Lead Attorney"},
             "detail": "Internal: hold the demand until the ortho surgical consult; consider policy-limits demand."},
        ]
        comms = [
            {"id": 20, "subject": "RE: Claim 55-1234 — IME request", "type": "EmailCommunication",
             "date": "2026-09-29", "senders": [{"id": 701, "name": "Pat Adjuster", "type": "Contact"}],
             "receivers": [{"id": 2, "name": "Lead Attorney", "type": "User"}],
             "body": "<p>We are requesting an independent medical examination before evaluating the demand. "
                     "Coverage is confirmed under policy SM-778 with BI limits of $100,000/$300,000.</p>"},
            {"id": 21, "subject": "Records request — PT visits", "type": "EmailCommunication", "date": "2026-09-20",
             "senders": [{"id": 1, "name": "Paralegal One", "type": "User"}],
             "receivers": [{"id": 602, "name": "Bayview Physical Therapy", "type": "Contact"}],
             "body": "Please send treatment records and an itemized bill for visits from 06/01/2026 to 09/01/2026."},
        ]
        tasks = [
            {"id": 40, "name": "Request PT records 06/01–09/01", "status": "pending", "due_at": "2026-09-25",
             "assignee": {"id": 1, "name": "Paralegal One", "type": "User"},
             "description": "Follow up with Bayview Physical Therapy for records and itemized bill."},
            {"id": 41, "name": "Draft demand letter", "status": "pending", "due_at": "2026-11-01",
             "assignee": {"id": 2, "name": "Lead Attorney", "type": "User"}, "description": ""},
        ]
        cal = [{"id": 70, "summary": "IME appointment", "start_at": "2026-10-15T09:00:00Z",
                "end_at": "2026-10-15T10:00:00Z", "description": "Defense IME requested by carrier."}]
        docs = [{"id": 10, "name": "ER and MRI records.pdf", "content_type": "application/pdf",
                 "created_at": "2025-04-03T10:00:00Z", "document_category": {"id": 1, "name": "Medical Records"}}]
        acts = [
            {"id": 50, "type": "ExpenseEntry", "date": "2025-07-01", "quantity": 1, "price": 85.0, "total": 85.0,
             "expense_category": {"id": 1, "name": "Medical records fee"}, "note": "Records fee - Lakeside"},
            {"id": 51, "type": "ExpenseEntry", "date": "2026-09-02", "quantity": 1, "price": 1200.0, "total": 1200.0,
             "expense_category": {"id": 2, "name": "Expert review"}, "note": ""},
        ]
        mrd = [
            {"id": 80, "medical_provider": {"id": 601, "name": "Lakeside Orthopedics"},
             "treatment_start_date": "2025-04-10", "treatment_end_date": "2026-09-12", "record_status": "received",
             "medical_bills": [{"id": 81, "name": "Ortho care", "amount": 22140.0, "bill_date": "2025-05-02",
                                "balance": 18000.0, "adjustment": 0, "mark_balance_as_lien": True}]},
            {"id": 82, "medical_provider": {"id": 602, "name": "Bayview Physical Therapy"},
             "treatment_start_date": "2025-04-15", "treatment_end_date": None, "record_status": "requested",
             "record_request_date": "2026-09-20",
             "medical_bills": [{"id": 83, "name": "PT", "amount": 9400.0, "bill_date": "2025-08-30",
                                "balance": 9400.0, "mark_balance_as_lien": True}]},
        ]
        return {
            "matter": matter, "contacts": {501: client, 601: ortho, 602: pt, 701: adjuster},
            "/notes.json": notes, "/communications.json": comms, "/tasks.json": tasks,
            "/calendar_entries.json": cal, "/documents.json": docs, "/activities.json": acts, "/bills.json": [],
            "/medical_records_details.json": mrd, "/damages.json": [
                {"id": 90, "amount": 6000.0, "damage_type": "special", "description": "Lost wages (6 weeks)"}],
            "/matter_stages.json": [{"id": 1, "name": "Intake"}, {"id": 2, "name": "Treatment"},
                                    {"id": 3, "name": "Demand"}, {"id": 4, "name": "Negotiation"},
                                    {"id": 5, "name": "Settlement"}],
            "/users.json": [{"id": 1, "name": "Paralegal One", "email": "p1@firm.test"},
                            {"id": 2, "name": "Lead Attorney", "email": "lead@firm.test"}],
            f"/matters/{MATTER_ID}/related_contacts.json": [],
            "files": {10: (_pdf_bytes(), "application/pdf")},
        }
