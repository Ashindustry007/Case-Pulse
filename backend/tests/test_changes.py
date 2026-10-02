"""Attorney endpoints end-to-end against the offline FakeClio (no LLM needed): F1 visits/changes, F3 citations on
structured facts, F4 deterministic worth range, providers, deadlines, Source Drawer endpoints."""
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.auth import create_user
from backend.app.db import connect
from backend.app.documents.processor import process_matter_documents
from backend.app.rag.index import build_index
from backend.app.sync.engine import sync_matter
from backend.tests.fake_clio import MATTER_ID


@pytest.fixture()
def client(tmp_db, fake_clio):
    from backend.app.main import app

    sync_matter(MATTER_ID, client=fake_clio)
    with connect() as db:
        process_matter_documents(db, fake_clio, MATTER_ID)
        build_index(db, MATTER_ID)
        create_user(db, "atty@test.local", "pw-123456", "Atty", "attorney")
        create_user(db, "prov@test.local", "pw-123456", "Prov", "provider", provider_contact_id=601)
    c = TestClient(app)
    assert c.post("/api/auth/login", json={"email": "atty@test.local", "password": "pw-123456"}).status_code == 200
    c.fake = fake_clio
    return c


def test_attorney_endpoints_are_cited(client):
    m = MATTER_ID
    ov = client.get(f"/api/matters/{m}/overview").json()
    assert ov["date_of_incident"]["value"] == "2025-03-14" and ov["date_of_incident"]["citations"]
    assert ov["statute_of_limitations"]["value"] == "2027-03-14"
    assert ov["medical_specials"]["value"] == 31540.0 and len(ov["medical_specials"]["citations"]) == 2
    assert ov["firm_spend"]["value"] == 1285.0
    assert ov["client"]["name"] == "Alex Sample" and ov["client"]["age"] is not None
    assert ov["stage"]["current"] == "Treatment" and ov["stage"]["index"] == 1

    provs = client.get(f"/api/matters/{m}/providers").json()["providers"]
    ortho = next(p for p in provs if p["name"] == "Lakeside Orthopedics")
    assert ortho["billed"]["value"] == 22140.0 and ortho["balance"]["value"] == 18000.0 and ortho["lien"]

    dl = client.get(f"/api/matters/{m}/deadlines").json()
    assert any(d["kind"] == "sol" for d in dl["upcoming"] + dl["overdue"])
    assert all(d["citations"] for d in dl["overdue"] + dl["upcoming"])

    costs = client.get(f"/api/matters/{m}/costs").json()
    assert costs["total"]["value"] == 1285.0 and costs["by_category"]

    brief = client.get(f"/api/matters/{m}/brief").json()
    w = brief["worth"]
    assert w["label"] == "Estimate" and w["low"] < w["high"]
    labels = {a["label"]: a for a in w["assumptions"]}
    assert labels["Bills total"]["citations"] and labels["Injury severity"]["not_found"]  # no LLM run → not found
    assert brief["coverage"]["um_uim"]["not_found"]

    tl = client.get(f"/api/matters/{m}/timeline").json()
    assert tl["total"] > 10 and all(i["citations"] for i in tl["items"])

    rec = client.get("/api/records/note:1").json()
    cit = tl["items"][0]["citations"][0]
    src = client.get(f"/api/records/{cit['record_id']}").json()
    assert src["body_text"][cit["char_start"]:cit["char_end"]] == cit["excerpt"]
    assert "rear-ended" in rec["body_text"]
    page = client.get("/api/documents/document:10/pages/1").json()
    assert page["method"] == "text_layer" and page["image_url"]
    assert client.get(page["image_url"]).headers["content-type"] == "image/png"
    assert client.get("/api/documents/document:10/file").status_code == 200


def test_visits_and_changes_f1(client):
    m = MATTER_ID
    v1 = client.post(f"/api/matters/{m}/visits").json()
    assert v1["first_visit"] and v1["previous_visit_at"] is None
    first = client.get(f"/api/matters/{m}/changes").json()
    assert first["first_visit"]
    # reload within the session keeps the same baseline
    assert client.post(f"/api/matters/{m}/visits").json()["visit_id"] == v1["visit_id"]

    # simulate: session ended (> 30 min ago), then the note changes in Clio and gets re-synced
    with connect() as db:
        db.execute("UPDATE matter_visits SET last_seen_at='2026-01-01T00:00:00Z' WHERE id=?", (v1["visit_id"],))
    time.sleep(1.1)
    client.fake.edit_note(2, "Client called: PT discharged, pain 3/10.")
    sync_matter(MATTER_ID, client=client.fake)
    v2 = client.post(f"/api/matters/{m}/visits").json()
    assert v2["previous_visit_at"] == "2026-01-01T00:00:00Z" and not v2["first_visit"]
    ch = client.get(f"/api/matters/{m}/changes", params={"since": v2["previous_visit_at"]}).json()
    assert ch["items"]  # everything synced after the baseline
    # a fresh baseline after the edit → explicit "nothing changed" message, no stale badges
    with connect() as db:
        db.execute("UPDATE matter_visits SET last_seen_at='2099-01-01T00:00:00Z' WHERE id=?", (v2["visit_id"],))
    none = client.get(f"/api/matters/{m}/changes", params={"since": "2099-01-01T00:00:00Z"}).json()
    assert none["items"] == [] and none["empty_message"].startswith("Nothing has changed since your last visit")
    assert none["last_activity"]["citations"]


def test_provider_role_is_blocked(client):
    p = TestClient(client.app)
    p.post("/api/auth/login", json={"email": "prov@test.local", "password": "pw-123456"})
    for path in (f"/api/matters/{MATTER_ID}/overview", "/api/records/note:3", f"/api/matters/{MATTER_ID}/brief",
                 "/api/ai-costs", "/api/documents/document:10/file"):
        assert p.get(path).status_code == 403, path
