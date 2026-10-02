"""Per-field case details (Clio custom fields): the attorney chooses exactly which details a provider sees."""
from backend.app.db import connect, jdump, now_iso
from backend.tests.dev2_support import EMAILS, MATTER, PROV_A, api, db_path, seeded  # noqa: F401


def _add_details(path):
    now = now_iso()
    with connect(path) as db:
        for i, (name, value, conf) in enumerate((("Date of Incident", "2023-04-23", 0),
                                                 ("Claim Number", "C-123", 0),
                                                 ("Case Value Rationale", "Economics alone come to ...", 0),
                                                 ("Treatment Status", "Active and ongoing", 1))):
            rid = f"custom_field:{MATTER}:f{i}"
            db.execute("INSERT INTO records(id, matter_id, type, title, body_text, meta, content_hash, first_seen_at, "
                       "last_changed_at) VALUES (?,?,?,?,?,?,?,?,?)",
                       (rid, MATTER, "custom_field", f"Custom field · {name}", f"{name}: {value}",
                        jdump({"field_name": name, "value": value}), rid, now, now))
            db.execute("INSERT INTO digests(record_id, matter_id, content_hash, confidential, created_at) "
                       "VALUES (?,?,?,?,?)", (rid, MATTER, rid, conf, now))


def test_candidates_list_details_with_confidentiality(api, seeded):
    _add_details(seeded)
    c = api("attorney").get(f"/api/matters/{MATTER}/share-candidates", params={"provider_contact_id": PROV_A}).json()
    opts = {o["label"]: o for o in c["case_detail_options"]}
    assert opts["Date of Incident"]["recommended"] and not opts["Date of Incident"]["confidential"]
    assert opts["Case Value Rationale"]["confidential"]          # flagged by name (strategy/valuation)
    assert opts["Treatment Status"]["confidential"]              # flagged by the digest
    assert len(c["case"]["case_details"]) == 4                   # preview projection has everything


def test_provider_sees_only_chosen_details(api, seeded):
    _add_details(seeded)
    att = api("attorney")
    g = att.post("/api/shares", json={"matter_id": MATTER, "provider_contact_id": PROV_A, "email": EMAILS["a"]}).json()
    chosen = [f"custom_field:{MATTER}:f0", f"custom_field:{MATTER}:f1"]
    r = att.post(f"/api/shares/{g['id']}/release", json={"fields": ["status", "case_details"], "case_fields": chosen})
    assert r.status_code == 200 and r.json()["policy"]["case_fields"] == chosen
    case = api("a").get(f"/api/provider/cases/{g['id']}").json()
    assert case["case_details"] == [{"label": "Date of Incident", "value": "2023-04-23"},
                                    {"label": "Claim Number", "value": "C-123"}]
    # v2 drops case_details entirely → the key is absent, not empty
    att.post(f"/api/shares/{g['id']}/release", json={"fields": ["status"], "case_fields": chosen})
    assert "case_details" not in api("a").get(f"/api/provider/cases/{g['id']}").json()
    audit = att.get(f"/api/shares/{g['id']}/audit").json()
    assert set(audit["versions"][1]["removed"]) >= set(chosen)


def test_release_rejects_foreign_case_fields(api, seeded):
    att = api("attorney")
    g = att.post("/api/shares", json={"matter_id": MATTER, "provider_contact_id": PROV_A, "email": EMAILS["a"]}).json()
    r = att.post(f"/api/shares/{g['id']}/release", json={"fields": ["case_details"], "case_fields": ["custom_field:999:x"]})
    assert r.status_code == 400
