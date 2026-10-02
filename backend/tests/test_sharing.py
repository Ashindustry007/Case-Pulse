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
