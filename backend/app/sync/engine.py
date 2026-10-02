"""Sync engine: pull every resource of a matter from Clio (GET only) into `records`, with change tracking (F1).

- content_hash per record; `first_seen_at` on insert; `last_changed_at` only when the hash changes;
  `deleted_at` when an item disappears on a full sync.
- Matter stage/status changes become synthetic `matter_event` records ("Case moved to Demand stage").
- Incremental by default (`updated_since` per resource); `full=True` re-pulls everything and detects deletions.
- Each resource is pulled independently: one failing resource (e.g. PI add-on not enabled) never aborts the sync.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

from ..clio.client import ClioClient
from ..config import settings
from ..db import connect, jdump, now_iso
from . import render as R

log = logging.getLogger("casepulse.sync")
_sync_lock = threading.Lock()

# ---- Clio field presets (nested selection). Fields this account rejects are pruned automatically by ClioClient. ----
CFV = "custom_field_values{id,field_name,field_type,value,picklist_option{id,option}}"
F_MATTER_LIST = "id,display_number,description,status,updated_at,client{id,name}"
F_MATTER = ("id,etag,number,display_number,description,status,open_date,close_date,pending_date,created_at,updated_at,"
            "client{id,name,type},practice_area{id,name},matter_stage{id,name},responsible_attorney{id,name,email},"
            f"originating_attorney{{id,name}},relationships{{id,description,contact{{id,name,type}}}},{CFV}")
F_CONTACT = ("id,etag,name,first_name,last_name,type,title,date_of_birth,created_at,updated_at,primary_email_address,"
             "primary_phone_number,email_addresses{address,name,primary},phone_numbers{number,name,primary},"
             f"avatar,company{{id,name}},{CFV}")
F_RELATED = "id,name,type,is_matter_client,relationship{id,description},primary_email_address,primary_phone_number"
F_NOTE = "id,etag,subject,detail,date,created_at,updated_at,type,author{id,name},matter{id}"
F_COMM = ("id,etag,subject,body,type,date,received_at,created_at,updated_at,senders{id,name,type},"
          "receivers{id,name,type},user{id,name},matter{id}")
F_TASK = ("id,etag,name,description,status,priority,due_at,completed_at,created_at,updated_at,"
          "assignee{id,name,type},assigner{id,name},matter{id},task_type{id,name}")
F_CAL = ("id,etag,summary,description,location,start_at,end_at,all_day,created_at,updated_at,matter{id},"
         "calendar_owner{id,name},attendees{id,name,type}")
F_DOC = ("id,etag,name,content_type,created_at,updated_at,received_at,size,parent{id,name},"
         "document_category{id,name},latest_document_version{id,size,content_type,created_at},matter{id},creator{id,name}")
F_ACT = ("id,etag,type,date,quantity,price,total,note,created_at,updated_at,user{id,name},"
         "activity_description{id,name},expense_category{id,name},matter{id},reference")
F_BILL = "id,etag,number,issued_at,due_at,total,balance,state,created_at,updated_at,subject"
F_MED_BILL = ("id,etag,name,amount,bill_date,bill_received_date,adjustment,balance,mark_balance_as_lien,created_at,"
              "updated_at,payers{amount,mark_as_lien,holder{id,name}}")
F_MRD = ("id,etag,description,treatment_start_date,treatment_end_date,in_treatment,record_status,bill_status,"
         "record_request_date,bill_request_date,created_at,updated_at,medical_provider{id,name},"
         f"medical_bills{{{F_MED_BILL}}}")
F_DAMAGE = "id,etag,amount,damage_type,description,created_at,updated_at"
F_STAGE = "id,name,practice_area{id,name}"
F_USER = "id,name,email"


def _hash(*parts: Any) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()


def _since(ts: str | None) -> str | None:
    if not ts:
        return None
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) - timedelta(minutes=2)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class MatterSync:
    def __init__(self, db: sqlite3.Connection, client: ClioClient, matter_id: int, full: bool) -> None:
        self.db, self.c, self.matter_id, self.full = db, client, matter_id, full
        self.now = now_iso()
        self.counts: dict[str, int] = {}
        self.errors: dict[str, str] = {}
        self.new = self.changed = self.removed = 0
        self.seen: dict[str, set[str]] = {}
        self.matter_url = f"{settings.clio_base_url}/nc/#/matters/{matter_id}"

    # ---------------------------------------------------------------- record upsert with change tracking
    def upsert(self, rtype: str, clio_id: Any, r: R.Rendered, raw: Any, *, rid: str | None = None,
               clio_updated_at: str | None = None) -> None:
        rid = rid or f"{rtype}:{clio_id}"
        self.seen.setdefault(rtype, set()).add(rid)
        h = _hash(r.title, r.body_text, r.meta, r.occurred_at)
        row = self.db.execute("SELECT content_hash, deleted_at FROM records WHERE id=?", (rid,)).fetchone()
        if row is None:
            self.db.execute(
                """INSERT INTO records(id, matter_id, type, clio_id, title, body_text, occurred_at, author, participants,
                     meta, raw, clio_url, content_hash, clio_updated_at, first_seen_at, last_changed_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rid, self.matter_id, rtype, str(clio_id), r.title, r.body_text, r.occurred_at, r.author,
                 jdump(r.participants), jdump(r.meta), jdump(raw), self.matter_url, h, clio_updated_at, self.now,
                 self.now))
            self.new += 1
        elif row["content_hash"] != h or row["deleted_at"]:
            self.db.execute(
                """UPDATE records SET title=?, body_text=?, occurred_at=?, author=?, participants=?, meta=?, raw=?,
                     content_hash=?, clio_updated_at=?, last_changed_at=?, deleted_at=NULL WHERE id=?""",
                (r.title, r.body_text, r.occurred_at, r.author, jdump(r.participants), jdump(r.meta), jdump(raw), h,
                 clio_updated_at, self.now, rid))
            self.changed += 1

    def mark_deleted(self, rtype: str) -> None:
        if not self.full or rtype in self.errors:
            return
        seen = self.seen.get(rtype, set())
        rows = self.db.execute("SELECT id FROM records WHERE matter_id=? AND type=? AND deleted_at IS NULL",
                               (self.matter_id, rtype)).fetchall()
        for row in rows:
            if row["id"] not in seen:
                self.db.execute("UPDATE records SET deleted_at=?, last_changed_at=? WHERE id=?",
                                (self.now, self.now, row["id"]))
                self.removed += 1

    def last_sync(self, resource: str) -> str | None:
        if self.full:
            return None
        row = self.db.execute("SELECT last_synced_at FROM sync_state WHERE matter_id=? AND resource=?",
                              (self.matter_id, resource)).fetchone()
        return _since(row["last_synced_at"]) if row else None

    def done(self, resource: str, n: int) -> None:
        self.counts[resource] = n
        self.db.execute("""INSERT INTO sync_state(matter_id, resource, last_synced_at, item_count) VALUES (?,?,?,?)
                           ON CONFLICT(matter_id, resource) DO UPDATE SET last_synced_at=excluded.last_synced_at,
                           item_count=excluded.item_count""", (self.matter_id, resource, self.now, n))

    def step(self, resource: str, fn: Callable[[], int]) -> None:
        try:
            self.done(resource, fn())
        except Exception as e:  # noqa: BLE001 — one resource failing must not abort the sync
            self.errors[resource] = str(e)[:300]
            log.warning("sync %s failed: %s", resource, e)

    def list_items(self, path: str, fields: str, resource: str, **params: Any) -> Iterable[dict]:
        return self.c.paginate(path, fields=fields, matter_id=self.matter_id,
                               updated_since=self.last_sync(resource), **params)

    # ---------------------------------------------------------------- resources
    def run(self) -> dict:
        self.step("matter", self.sync_matter)
        self.step("contacts", self.sync_contacts)
        self.step("notes", lambda: self._simple("/notes.json", F_NOTE, "notes", "note", R.note, type="Matter"))
        self.step("communications", lambda: self._simple("/communications.json", F_COMM, "communications",
                                                          "communication", R.communication))
        self.step("tasks", lambda: self._simple("/tasks.json", F_TASK, "tasks", "task", R.task))
        self.step("calendar_entries", lambda: self._simple("/calendar_entries.json", F_CAL, "calendar_entries",
                                                           "calendar_entry", R.calendar_entry))
        self.step("documents", lambda: self._simple("/documents.json", F_DOC, "documents", "document", R.document))
        self.step("activities", self.sync_activities)
        self.step("bills", lambda: self._simple("/bills.json", F_BILL, "bills", "bill", R.bill))
        self.step("medical_records", self.sync_medical)
        self.step("damages", lambda: self._simple("/damages.json", F_DAMAGE, "damages", "damage", R.damage))
        for rtype in ("note", "communication", "task", "calendar_entry", "document", "expense", "time_entry", "bill",
                      "medical_record", "medical_bill", "damage", "custom_field"):
            self.mark_deleted(rtype)
        return {"counts": self.counts, "errors": self.errors, "new": self.new, "changed": self.changed,
                "removed": self.removed}

    def _simple(self, path: str, fields: str, resource: str, rtype: str, fn: Callable[[dict], R.Rendered],
                **params: Any) -> int:
        n = 0
        for item in self.list_items(path, fields, resource, **params):
            self.upsert(rtype, item["id"], fn(item), item, clio_updated_at=item.get("updated_at"))
            n += 1
        return n

    def sync_matter(self) -> int:
        m = self.c.get(f"/matters/{self.matter_id}.json", fields=F_MATTER)["data"]
        prev = self.db.execute("SELECT status, stage_name FROM matters WHERE id=?", (self.matter_id,)).fetchone()
        stage = m.get("matter_stage") or {}
        self.db.execute(
            """INSERT INTO matters(id, display_number, description, status, stage_id, stage_name, practice_area, client_id,
                 open_date, close_date, clio_url, raw, synced_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET display_number=excluded.display_number, description=excluded.description,
                 status=excluded.status, stage_id=excluded.stage_id, stage_name=excluded.stage_name,
                 practice_area=excluded.practice_area, client_id=excluded.client_id, open_date=excluded.open_date,
                 close_date=excluded.close_date, raw=excluded.raw, synced_at=excluded.synced_at""",
            (m["id"], m.get("display_number"), m.get("description"), m.get("status"), stage.get("id"),
             stage.get("name"), R.name_of(m.get("practice_area")), (m.get("client") or {}).get("id"),
             m.get("open_date"), m.get("close_date"), self.matter_url, jdump(m), self.now))
        # Stage/status movement → synthetic matter_event records (F1 + provider "last movement").
        if prev is not None:
            for label, old, new in (("stage", prev["stage_name"], stage.get("name")),
                                    ("status", prev["status"], m.get("status"))):
                if new and old != new:
                    text = (f"Case moved to {new} stage" if label == "stage" else f"Matter status changed to {new}")
                    body = f"Matter event: {text}\nPrevious {label}: {old or 'none'}\nDate: {self.now}"
                    self.upsert("matter_event", f"{self.matter_id}-{label}-{self.now}",
                                R.Rendered(title=text, body_text=body, occurred_at=self.now,
                                           meta={"event": label, "from": old, "to": new, "provider_safe": True}),
                                {"from": old, "to": new})
        # Custom fields → one citable record each.
        n = 0
        for cfv in m.get("custom_field_values") or []:
            r = R.custom_field(cfv)
            if r:
                self.upsert("custom_field", cfv.get("id"), r, cfv, rid=f"custom_field:{self.matter_id}:{cfv.get('id')}")
                n += 1
        # Stage catalogue (for the stage progress bar) + firm users (internal vs external).
        try:
            for s in self.c.paginate("/matter_stages.json", fields=F_STAGE):
                self.db.execute("""INSERT INTO matter_stages(id, name, practice_area, sort_order) VALUES (?,?,?,?)
                                   ON CONFLICT(id) DO UPDATE SET name=excluded.name, practice_area=excluded.practice_area""",
                                (s["id"], s.get("name"), R.name_of(s.get("practice_area")), s["id"]))
        except Exception as e:  # noqa: BLE001
            self.errors["matter_stages"] = str(e)[:200]
        try:
            for u in self.c.paginate("/users.json", fields=F_USER):
                self.db.execute("INSERT OR REPLACE INTO firm_users(id, name, email, raw) VALUES (?,?,?,?)",
                                (u["id"], u.get("name"), u.get("email"), jdump(u)))
        except Exception as e:  # noqa: BLE001
            self.errors["users"] = str(e)[:200]
        self._matter = m
        return 1 + n

    def sync_contacts(self) -> int:
        m = getattr(self, "_matter", None) or {}
        rels: dict[int, dict] = {}
        client = m.get("client") or {}
        if client.get("id"):
            rels[client["id"]] = {"relationship": "Client", "is_client": True}
        for rel in m.get("relationships") or []:
            cid = (rel.get("contact") or {}).get("id")
            if cid:
                rels.setdefault(cid, {"relationship": rel.get("description"), "is_client": False})
        try:
            for rc in self.c.paginate(f"/matters/{self.matter_id}/related_contacts.json", fields=F_RELATED):
                rel_desc = R.name_of(rc.get("relationship")) if isinstance(rc.get("relationship"), dict) else rc.get(
                    "relationship")
                cur = rels.setdefault(rc["id"], {"relationship": rel_desc, "is_client": bool(rc.get("is_matter_client"))})
                cur["relationship"] = cur.get("relationship") or rel_desc
                cur["is_client"] = cur["is_client"] or bool(rc.get("is_matter_client"))
        except Exception as e:  # noqa: BLE001
            self.errors["related_contacts"] = str(e)[:200]
        self._contact_rels = rels
        n = 0
        for cid, info in rels.items():
            n += self._sync_contact(cid, info.get("relationship"), info.get("is_client", False))
        return n

    def _sync_contact(self, cid: int, relationship: str | None, is_client: bool) -> int:
        try:
            c = self.c.get(f"/contacts/{cid}.json", fields=F_CONTACT)["data"]
        except Exception as e:  # noqa: BLE001
            self.errors[f"contact:{cid}"] = str(e)[:200]
            return 0
        role = "client" if is_client else R.classify_role(relationship, c.get("name"), c.get("title"),
                                                          R.name_of(c.get("company")))
        r = R.contact(c, relationship, role)
        avatar = c.get("avatar")
        avatar_url = avatar.get("url") if isinstance(avatar, dict) else (avatar if isinstance(avatar, str) else None)
        self.db.execute(
            """INSERT INTO contacts(id, name, type, email, phone, avatar_url, raw, synced_at) VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET name=excluded.name, type=excluded.type, email=excluded.email,
                 phone=excluded.phone, avatar_url=excluded.avatar_url, raw=excluded.raw, synced_at=excluded.synced_at""",
            (cid, r.meta["name"], c.get("type"), r.meta["email"], r.meta["phone"], avatar_url, jdump(c), self.now))
        self.db.execute("""INSERT OR REPLACE INTO matter_contacts(matter_id, contact_id, relationship, is_client, role)
                           VALUES (?,?,?,?,?)""", (self.matter_id, cid, relationship or "", int(is_client), role))
        self.upsert("contact", cid, r, c, rid=f"contact:{cid}", clio_updated_at=c.get("updated_at"))
        return 1

    def sync_activities(self) -> int:
        n = 0
        for a in self.list_items("/activities.json", F_ACT, "activities"):
            kind, r = R.activity(a)
            self.upsert(kind, a["id"], r, a, clio_updated_at=a.get("updated_at"))
            n += 1
        return n

    def sync_medical(self) -> int:
        n = 0
        known = getattr(self, "_contact_rels", {})
        for mrd in self.list_items("/medical_records_details.json", F_MRD, "medical_records"):
            prov = mrd.get("medical_provider") or {}
            pid, pname = prov.get("id"), R.name_of(prov)
            if pid and pid not in known:  # make sure every provider is a known, citable contact
                known[pid] = {"relationship": "Medical provider", "is_client": False}
                self._sync_contact(pid, "Medical provider", False)
            elif pid:
                self.db.execute("UPDATE matter_contacts SET role='medical_provider' WHERE matter_id=? AND contact_id=?",
                                (self.matter_id, pid))
            self.upsert("medical_record", mrd["id"], R.medical_record(mrd, pname), mrd,
                        clio_updated_at=mrd.get("updated_at"))
            n += 1
            for b in mrd.get("medical_bills") or []:
                self.upsert("medical_bill", b["id"], R.medical_bill(b, pname, pid), b,
                            clio_updated_at=b.get("updated_at"))
                n += 1
        return n


# ------------------------------------------------------------------------------------------------------------------
def list_clio_matters(client: ClioClient | None = None) -> list[dict]:
    c = client or ClioClient()
    return list(c.paginate("/matters.json", fields=F_MATTER_LIST, status="open,pending,closed"))


def sync_matter(matter_id: int, *, full: bool | None = None, client: ClioClient | None = None) -> dict:
    """Sync one matter. Full on first sync (or when asked), incremental afterwards."""
    with _sync_lock:
        c = client or ClioClient()
        started = now_iso()
        with connect() as db:
            if full is None:
                full = db.execute("SELECT 1 FROM sync_state WHERE matter_id=? LIMIT 1", (matter_id,)).fetchone() is None
            s = MatterSync(db, c, matter_id, full)
            res = s.run()
        res.update({"matter_id": matter_id, "started_at": started, "finished_at": now_iso(), "full": full,
                    "requests": c.requests_made})
        return res


def last_synced_at(db: sqlite3.Connection, matter_id: int | None = None) -> str | None:
    row = db.execute("SELECT MAX(last_synced_at) FROM sync_state WHERE (? IS NULL OR matter_id=?)",
                     (matter_id, matter_id)).fetchone()
    return row[0] if row else None


def fresh_enough(db: sqlite3.Connection, matter_id: int, minutes: int = 3) -> bool:
    ts = last_synced_at(db, matter_id)
    if not ts:
        return False
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.now(timezone.utc) - dt < timedelta(minutes=minutes)
