"""[Dev 2] Test support for test_rbac.py / test_sharing.py.

Deliberately NOT conftest.py (that file would be shared with Dev 1). Import what you need:
    from backend.tests.dev2_support import api, db_path, seeded  # noqa: F401  (pytest fixtures)
Seeds Dev 1's tables in a TEMP database only, in the shapes agreed in docs/workstreams/interface-dev1-dev2.md.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.auth import create_user
from backend.app.db import connect, get_db, jdump, migrate, now_iso
from backend.app.main import app
from backend.app.sharing import sources

PASSWORD = "correct-horse-1"
EMAILS = {"attorney": "attorney@firm.test", "a": "provider-a@clinic.test", "b": "provider-b@clinic.test"}
MATTER, CLIENT, PROV_A, PROV_B = 1001, 100, 600, 601


def days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def cit(record_id: str, source_type: str = "note", excerpt: str = "source text") -> dict:
    return {"record_id": record_id, "source_type": source_type, "title": record_id,
            "char_start": 0, "char_end": len(excerpt), "excerpt": excerpt}


def seed(db, *, with_case_data: bool = True) -> dict[str, int]:
    now = now_iso()
    uid = {
        "attorney": create_user(db, EMAILS["attorney"], PASSWORD, "Firm Attorney", "attorney"),
        "a": create_user(db, EMAILS["a"], PASSWORD, "Provider A", "provider", PROV_A),
        "b": create_user(db, EMAILS["b"], PASSWORD, "Provider B", "provider", PROV_B),
    }
    db.execute("INSERT INTO matters(id, display_number, description, status, stage_name, practice_area, client_id, "
               "synced_at) VALUES (?,?,?,?,?,?,?,?)",
               (MATTER, "00001", "Test matter", "open", "Demand", "Personal Injury", CLIENT, now))
    for cid, name, email in ((CLIENT, "Pat Example", None), (PROV_A, "Provider A Clinic", EMAILS["a"]),
                             (PROV_B, "Provider B Clinic", EMAILS["b"])):
        db.execute("INSERT INTO contacts(id, name, type, email, synced_at) VALUES (?,?,?,?,?)",
                   (cid, name, "Company", email, now))
    for i, name in enumerate(("Intake", "Treatment", "Demand", "Settlement")):
        db.execute("INSERT INTO matter_stages(id, name, practice_area, sort_order) VALUES (?,?,?,?)",
                   (i + 1, name, "Personal Injury", i))
    if not with_case_data:
        return uid

    def rec(rid: str, type_: str, title: str, occurred: str, meta: dict | None = None) -> None:
        db.execute("INSERT INTO records(id, matter_id, type, title, body_text, occurred_at, meta, content_hash, "
                   "first_seen_at, last_changed_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (rid, MATTER, type_, title, title, occurred, jdump(meta or {}), rid, now, now))

    def digest(rid: str, confidential: int, safe: str | None) -> None:
        db.execute("INSERT INTO digests(record_id, matter_id, content_hash, confidential, provider_safe_summary, "
                   "created_at) VALUES (?,?,?,?,?,?)", (rid, MATTER, rid, confidential, safe, now))

    rec("communication:1", "communication", "ER records received", days_ago(10))
    digest("communication:1", 0, "ER records received")
    rec("note:2", "note", "Internal strategy discussion", days_ago(3))
    digest("note:2", 1, None)
    rec("medical_bill:30", "medical_bill", "Bill A", days_ago(40),
        {"provider_contact_id": PROV_A, "amount": 1200.0, "balance": 900.0, "lien": True})
    rec("medical_bill:31", "medical_bill", "Bill B", days_ago(35),
        {"provider_contact_id": PROV_B, "amount": 500.0, "balance": None, "lien": False})
    rec("document:10", "document", "Imaging report", days_ago(30), {"file_path": "files/report.pdf"})
    rec("document:11", "document", "Internal memo", days_ago(5), {"file_path": "files/memo.pdf"})
    db.execute("INSERT INTO document_pages(document_id, page_no, text, method) VALUES "
               "('document:10', 1, 'p1', 'text_layer'), ('document:10', 2, 'p2', 'text_layer')")
    for rid, prov, kind, desc, ago, channel, addressed, cits in (
        ("req:1", PROV_A, "records", "Records for recent visits", 7, "task", 0, [cit("task:40", "task")]),
        ("req:2", PROV_A, "bills", "Itemized bill", 2, "email", 1,
         [cit("communication:41", "communication", "Please send an itemized bill")]),
        ("req:3", PROV_B, "records", "Records for B", 4, "task", 0, [cit("task:42", "task")]),
    ):
        db.execute("INSERT INTO provider_requests(id, matter_id, provider_contact_id, kind, description, requested_at, "
                   "channel, source_addressed_to_provider, citations, input_hash, created_at) "
                   "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   (rid, MATTER, prov, kind, desc, days_ago(ago), channel, addressed, jdump(cits), rid, now))
    nf = lambda label: {"not_found": True, "label": label}  # noqa: E731
    facts = [
        ("coverage", {"carrier": {"value": "Acme Mutual", "citations": [cit("document:10", "document", "Acme")]},
                      "bi_per_person": {"value": "$100,000", "citations": [cit("document:10", "document", "100k")]},
                      "bi_per_accident": nf("BI per accident"), "um_uim": nf("UM/UIM"), "medpay": nf("MedPay"),
                      "confirmed": True}),
        ("worth", {"label": "Estimate", "low": 3000.0, "high": 6000.0, "currency": "USD", "method": "specials x band",
                   "assumptions": [{"label": "Bills total", "text": "$1,700", "not_found": False,
                                    "citations": [cit("medical_bill:30", "medical_bill", "Bill A")]}]}),
        ("treatment_visit", {"provider_contact_id": PROV_A, "provider_name": "Provider A Clinic",
                             "date": days_ago(80), "description": None}),
        ("treatment_visit", {"provider_contact_id": PROV_A, "provider_name": "Provider A Clinic",
                             "date": days_ago(20), "description": None}),
        ("treatment_visit", {"provider_contact_id": PROV_B, "provider_name": "Provider B Clinic",
                             "date": days_ago(40), "description": None}),
    ]
    for kind, value in facts:
        db.execute("INSERT INTO facts(matter_id, kind, value, citations, input_hash, created_at) VALUES (?,?,?,?,?,?)",
                   (MATTER, kind, jdump(value), "[]", kind, now))
    return uid


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    migrate(path)

    def _get_db():
        with connect(path) as conn:
            yield conn

    app.dependency_overrides[get_db] = _get_db
    monkeypatch.setattr(sources, "data_dir", lambda: tmp_path)
    (tmp_path / "files").mkdir()
    (tmp_path / "files" / "report.pdf").write_bytes(b"%PDF-1.4 test report")
    yield path
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def seeded(db_path):
    with connect(db_path) as db:
        seed(db)
    return db_path


@pytest.fixture
def api(seeded):
    """Factory: api("attorney" | "a" | "b" | None) → TestClient with its own cookie jar, logged in."""

    def make(who: str | None = None) -> TestClient:
        client = TestClient(app)
        if who:
            r = client.post("/api/auth/login", json={"email": EMAILS[who], "password": PASSWORD})
            assert r.status_code == 200, r.text
        return client

    return make


def share(att: TestClient, *, contact: int = PROV_A, email: str = EMAILS["a"], fields=("status",), docs=(),
          detail: str = "confirmed", note: str | None = None) -> tuple[int, dict]:
    g = att.post("/api/shares", json={"matter_id": MATTER, "provider_contact_id": contact, "email": email})
    assert g.status_code == 200, g.text
    gid = g.json()["id"]
    r = att.post(f"/api/shares/{gid}/release", json={"fields": list(fields), "document_ids": list(docs),
                                                     "coverage_detail": detail, "status_note": note})
    assert r.status_code == 200, r.text
    return gid, r.json()


def new_invite(db_path, email: str, contact: int = PROV_A, *, revoked: bool = False) -> str:
    """Create a grant + invite directly (no release) and return the plaintext code."""
    from backend.app.sharing import invites

    with connect(db_path) as db:
        cur = db.execute("INSERT INTO share_grants(matter_id, provider_contact_id, email, created_at, revoked_at) "
                         "VALUES (?,?,?,?,?)", (MATTER, contact, email, now_iso(), now_iso() if revoked else None))
        return invites.create_invite(db, email, int(cur.lastrowid))
