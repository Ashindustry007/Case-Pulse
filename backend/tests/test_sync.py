"""Sync engine against the offline FakeClio: normalization, change tracking, stage events (F1 groundwork)."""
import time

from backend.app.db import connect
from backend.app.sync.engine import sync_matter
from backend.tests.fake_clio import MATTER_ID


def test_full_sync_then_incremental_change(tmp_db, fake_clio):
    res = sync_matter(MATTER_ID, client=fake_clio)
    assert res["full"] and not res["errors"], res["errors"]
    assert res["counts"]["notes"] == 3 and res["counts"]["medical_records"] == 4
    with connect() as db:
        types = dict(db.execute("SELECT type, COUNT(*) FROM records GROUP BY type").fetchall())
        assert types["medical_bill"] == 2 and types["expense"] == 2 and types["custom_field"] == 3
        assert types["contact"] == 4
        roles = dict(db.execute("SELECT contact_id, role FROM matter_contacts").fetchall())
        assert roles[501] == "client" and roles[601] == "medical_provider" and roles[701] == "insurer"
        body = db.execute("SELECT body_text FROM records WHERE id='medical_bill:81'").fetchone()[0]
        assert "Medical bill · Lakeside Orthopedics · $22,140.00 · 2025-05-02" in body
        email = db.execute("SELECT body_text FROM records WHERE id='communication:20'").fetchone()[0]
        assert "<p>" not in email and "independent medical examination" in email

    # nothing changed → no new/changed
    time.sleep(1.1)
    res2 = sync_matter(MATTER_ID, client=fake_clio)
    assert (res2["new"], res2["changed"], res2["removed"]) == (0, 0, 0)

    # edit a note + move the stage in "Clio"
    time.sleep(1.1)
    fake_clio.edit_note(2, "Client called: PT discharged, pain 3/10.")
    fake_clio.set_stage("Demand")
    res3 = sync_matter(MATTER_ID, client=fake_clio)
    assert res3["changed"] == 1 and res3["new"] == 1  # the note + one matter_event
    with connect() as db:
        ev = db.execute("SELECT title FROM records WHERE type='matter_event'").fetchone()[0]
        assert ev == "Case moved to Demand stage"
        n2 = db.execute("SELECT first_seen_at, last_changed_at FROM records WHERE id='note:2'").fetchone()
        assert n2[1] > n2[0]


def test_full_sync_detects_deletions(tmp_db, fake_clio):
    sync_matter(MATTER_ID, client=fake_clio)
    fake_clio.data["/notes.json"] = fake_clio.data["/notes.json"][:2]
    res = sync_matter(MATTER_ID, full=True, client=fake_clio)
    assert res["removed"] == 1
