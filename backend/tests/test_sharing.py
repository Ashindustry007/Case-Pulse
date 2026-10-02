"""[Dev 2] Sharing: invites, release/versioning, projection, events, request states (F5–F8)."""
from backend.app.db import connect
from backend.tests.dev2_support import (EMAILS, MATTER, PASSWORD, PROV_A, PROV_B, api, db_path,  # noqa: F401
                                        days_ago, new_invite, seeded, share)

# ---------------------------------------------------------------------------------------------------- invites (2.2)


def test_invite_accept_creates_provider_and_logs_in(api, seeded):
    code = new_invite(seeded, "new-provider@clinic.test")
    c = api()
    r = c.post(f"/api/auth/invite/{code}/accept", json={"password": "longpassword", "name": "New Provider"})
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "provider" and r.json()["provider_contact_id"] == PROV_A
    assert c.get("/api/auth/me").json()["email"] == "new-provider@clinic.test"
    with connect(seeded) as db:
        grant = db.execute("SELECT provider_user_id FROM share_grants WHERE email = ?",
                           ("new-provider@clinic.test",)).fetchone()
        assert grant["provider_user_id"] == r.json()["id"]
        assert db.execute("SELECT event FROM share_events").fetchone()["event"] == "invite_accepted"


def test_invite_cannot_be_reused(api, seeded):
    code = new_invite(seeded, "once@clinic.test")
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "longpassword"}).status_code == 200
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "otherpassword"}).status_code == 410


def test_expired_invite_rejected(api, seeded):
    code = new_invite(seeded, "late@clinic.test")
    with connect(seeded) as db:
        db.execute("UPDATE invites SET expires_at = '2000-01-01T00:00:00Z'")
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "longpassword"}).status_code == 410


def test_invite_for_revoked_grant_rejected(api, seeded):
    code = new_invite(seeded, "gone@clinic.test", revoked=True)
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "longpassword"}).status_code == 410


def test_invite_never_converts_an_attorney(api, seeded):
    code = new_invite(seeded, EMAILS["attorney"])
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "hijackpassword"}).status_code == 409
    # attorney password unchanged
    assert api().post("/api/auth/login", json={"email": EMAILS["attorney"], "password": PASSWORD}).status_code == 200


def test_second_invite_for_existing_provider_requires_their_password(api, seeded):
    code = new_invite(seeded, EMAILS["a"], PROV_B)
    assert api().post(f"/api/auth/invite/{code}/accept", json={"password": "wrongpassword"}).status_code == 401
    assert api().post("/api/auth/login", json={"email": EMAILS["a"], "password": PASSWORD}).status_code == 200
    c = api()
    r = c.post(f"/api/auth/invite/{code}/accept", json={"password": PASSWORD})
    assert r.status_code == 200, r.text
    assert r.json()["provider_contact_id"] == PROV_A
    with connect(seeded) as db:
        uid = db.execute("SELECT id FROM users WHERE email = ?", (EMAILS["a"],)).fetchone()["id"]
        grant = db.execute("SELECT provider_user_id FROM share_grants WHERE email = ?", (EMAILS["a"],)).fetchone()
        assert grant["provider_user_id"] == uid


def test_unknown_invite_404(api):
    assert api().post("/api/auth/invite/nope/accept", json={"password": "longpassword"}).status_code == 404


# ------------------------------------------------------------------------------------------- projection (2.6a, F6)
from datetime import date  # noqa: E402

from backend.app.contracts import SharePolicy  # noqa: E402
from backend.app.sharing import projection, sources  # noqa: E402


def _policy(fields, docs=(), detail="confirmed", note=None):
    return SharePolicy(grant_id=1, version=1, fields=list(fields), document_ids=list(docs), coverage_detail=detail,
                       status_note=note, released_at="2026-10-01T00:00:00Z")


def _case(db_path, fields, contact=PROV_A, **kw):
    with connect(db_path) as db:
        s = projection.build_sections(db, MATTER, contact)
    return projection.project(s, grant_id=1, policy=_policy(fields, **kw), shared_by="Firm Attorney").model_dump(
        mode="json", exclude_none=True)


def test_heartbeat_state_boundaries():
    today = date(2026, 10, 2)
    assert projection.heartbeat_state("open", "2026-09-02", today) == "active"     # 30d
    assert projection.heartbeat_state("open", "2026-09-01", today) == "quiet"      # 31d
    assert projection.heartbeat_state("open", "2026-07-04", today) == "quiet"      # 90d
    assert projection.heartbeat_state("open", "2026-07-03", today) == "dormant"    # 91d
    assert projection.heartbeat_state("Closed", "2026-10-01", today) == "closed"
    assert projection.heartbeat_state("open", None, today) == "dormant"


def test_only_granted_sections_exist(seeded):
    case = _case(seeded, ["status"])
    assert set(case) == {"grant_id", "policy_version", "patient_display", "firm_name", "shared_by", "updated_at",
                         "heartbeat"}
    assert case["patient_display"] == "P. E."


def test_every_field_maps_to_its_section(seeded):
    case = _case(seeded, projection.ALL_FIELDS, docs=["document:10"], detail="limits", note="Hello")
    for key in ("heartbeat", "coverage", "case_value", "bills", "requests", "documents", "adherence", "other_care",
                "status_note"):
        assert key in case, key


def test_last_movement_masks_confidential_activity(seeded):
    hb = _case(seeded, ["status"])["heartbeat"]
    assert hb["state"] == "active"
    assert hb["last_movement"] == {"date": days_ago(3), "text": "Case activity recorded"}
    assert [m["text"] for m in hb["recent_movement"]] == ["ER records received"]
    assert hb["stage"]["current"] == "Demand" and hb["stage"]["index"] == 2


def test_coverage_detail_variants(seeded):
    assert _case(seeded, ["coverage"])["coverage"] == {"confirmed": True}
    limits = _case(seeded, ["coverage"], detail="limits")["coverage"]
    assert limits["carrier"] == "Acme Mutual" and "BI per person $100,000" in limits["limits_text"]
    assert "UM/UIM" not in limits["limits_text"]          # not found → never invented


def test_sections_are_scoped_to_the_provider(seeded):
    a = _case(seeded, ["bills", "open_requests", "adherence", "other_care"])
    assert a["bills"]["billed"] == 1200.0 and a["bills"]["lien"] is True
    assert {r["id"] for r in a["requests"]} == {"req:1", "req:2"}
    assert len(a["adherence"]["visits"]) == 2 and a["adherence"]["gaps"][0]["days"] == 60
    assert [o["provider_name"] for o in a["other_care"]] == ["Provider B Clinic"]
    b = _case(seeded, ["bills", "open_requests"], contact=PROV_B)
    assert b["bills"]["billed"] == 500.0 and "balance" not in b["bills"]
    assert {r["id"] for r in b["requests"]} == {"req:3"}


def test_provider_sees_excerpt_only_when_addressed_to_them(seeded):
    reqs = {r["id"]: r for r in _case(seeded, ["open_requests"])["requests"]}
    assert reqs["req:1"]["citations"] == []
    assert reqs["req:2"]["citations"][0]["excerpt"] == "Please send an itemized bill"
    with connect(seeded) as db:
        full = projection.requests.requests_for(db, MATTER, PROV_A, audience="attorney")
    assert all(r.citations for r in full)


def test_documents_limited_to_policy(seeded):
    assert [d["id"] for d in _case(seeded, ["documents"], docs=["document:10"])["documents"]] == ["document:10"]
    assert _case(seeded, ["documents"])["documents"] == []


def test_empty_dev1_data_still_projects(db_path):
    from backend.tests.dev2_support import seed
    with connect(db_path) as db:
        seed(db, with_case_data=False)
    case = _case(db_path, projection.ALL_FIELDS)
    assert case["heartbeat"]["state"] == "dormant"
    for key in ("coverage", "case_value", "bills", "adherence", "other_care"):
        assert key not in case, key
    assert case["requests"] == [] and case["documents"] == []


def test_malformed_fact_is_ignored_not_fatal(seeded):
    with connect(seeded) as db:
        db.execute("INSERT INTO facts(matter_id, kind, value, citations, input_hash, created_at) "
                   "VALUES (?, 'coverage', '{\"carrier\": 1}', '[]', 'x', '2999-01-01T00:00:00Z')", (MATTER,))
        assert sources.coverage(db, MATTER) is None
    assert "coverage" not in _case(seeded, ["coverage"])
