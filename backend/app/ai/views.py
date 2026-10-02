"""Read models built from synced records + AI outputs. Every fact returned is Cited or NotFound (F3).

Dev 2's ProviderProjection may import these (read-only): `provider_summaries`, `heartbeat_inputs`,
`value.worth`, `value.coverage`, `open_requests`.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timezone

from ..contracts import (Citation, Cited, ClientContact, ClientInfo, CostCategory, Costs, DeadlineItem, Deadlines,
                         MatterSummary, MonthAmount, NotFound, Overview, ProviderSummary, StageInfo, TimelineItem,
                         Visit)
from ..db import jload
from ..rag.cite import record_citation
from . import value

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _days_between(a: str, b: str) -> int:
    return (date.fromisoformat(b[:10]) - date.fromisoformat(a[:10])).days


def _fact(db: sqlite3.Connection, matter_id: int, kind: str) -> tuple[dict, list[Citation]] | None:
    r = db.execute("SELECT value, citations FROM facts WHERE matter_id=? AND kind=? ORDER BY id DESC LIMIT 1",
                   (matter_id, kind)).fetchone()
    if not r:
        return None
    cits = [Citation(**c) for c in jload(r["citations"], [])]
    return (jload(r["value"], {}), cits) if cits else None


def _custom_field_date(db: sqlite3.Connection, matter_id: int, pattern: str) -> Cited[str] | None:
    for r in db.execute("SELECT * FROM records WHERE matter_id=? AND type='custom_field' AND deleted_at IS NULL",
                        (matter_id,)):
        meta = jload(r["meta"], {}) or {}
        if re.search(pattern, meta.get("field_name") or "", re.I) and DATE_RE.search(str(meta.get("value"))):
            return Cited[str](value=DATE_RE.search(str(meta["value"])).group(0),
                              citations=[record_citation(db, r["id"], rec=r)])
    return None


def key_date(db: sqlite3.Connection, matter_id: int, kind: str, label: str, cf_pattern: str) -> Cited[str] | NotFound:
    f = _fact(db, matter_id, kind)
    if f and DATE_RE.search(str(f[0].get("value"))):
        return Cited[str](value=DATE_RE.search(str(f[0]["value"])).group(0), citations=f[1])
    return _custom_field_date(db, matter_id, cf_pattern) or NotFound(label=label)


def matter_summary(db: sqlite3.Connection, m: sqlite3.Row) -> MatterSummary:
    client = db.execute("SELECT name FROM contacts WHERE id=?", (m["client_id"],)).fetchone()
    last = db.execute("""SELECT MAX(occurred_at) FROM records WHERE matter_id=? AND deleted_at IS NULL
                         AND type NOT IN ('contact','custom_field') AND occurred_at <= ?""",
                      (m["id"], today() + "T23:59:59Z")).fetchone()[0]
    return MatterSummary(id=m["id"], display_number=m["display_number"], description=m["description"],
                         status=m["status"], stage=m["stage_name"], client_name=client["name"] if client else None,
                         last_activity_at=last)


def stage_info(db: sqlite3.Connection, m: sqlite3.Row) -> StageInfo:
    rows = db.execute("""SELECT name FROM matter_stages WHERE practice_area = ? OR practice_area IS NULL
                         ORDER BY sort_order, id""", (m["practice_area"],)).fetchall() or db.execute(
        "SELECT name FROM matter_stages ORDER BY sort_order, id").fetchall()
    stages = [r["name"] for r in rows]
    idx = stages.index(m["stage_name"]) if m["stage_name"] in stages else None
    return StageInfo(current=m["stage_name"], stages=stages, index=idx)


def last_client_contact(db: sqlite3.Connection, matter_id: int) -> Cited[ClientContact] | NotFound:
    r = db.execute("""SELECT r.*, d.one_liner FROM digests d JOIN records r ON r.id=d.record_id
                      WHERE d.matter_id=? AND d.client_contact=1 AND r.deleted_at IS NULL AND r.occurred_at IS NOT NULL
                        AND r.occurred_at <= ? ORDER BY r.occurred_at DESC LIMIT 1""",
                   (matter_id, today() + "T23:59:59Z")).fetchone()
    if not r:
        return NotFound(label="Client contact")
    meta = jload(r["meta"], {}) or {}
    channel = {"communication": meta.get("channel") or "email", "note": "note", "calendar_entry": "meeting"}.get(
        r["type"], "other")
    if channel.startswith("phone"):
        channel = "call"
    at = r["occurred_at"]
    return Cited[ClientContact](value=ClientContact(at=at, days_ago=max(0, _days_between(at, today())),
                                                    channel=channel, by=r["author"], summary=r["one_liner"]),
                                citations=[record_citation(db, r["id"], rec=r)])


def client_info(db: sqlite3.Connection, m: sqlite3.Row) -> ClientInfo:
    c = db.execute("SELECT * FROM contacts WHERE id=?", (m["client_id"],)).fetchone()
    name = c["name"] if c else "Client"
    photo_url, photo_cit = None, None
    pf = _fact(db, m["id"], "client_photo")
    if pf and pf[0].get("document_id"):
        photo_url, photo_cit = f"/api/documents/{pf[0]['document_id']}/file", pf[1][0]
    elif c and c["avatar_url"]:
        photo_url = c["avatar_url"]
    dob: Cited[str] | NotFound = NotFound(label="Date of birth")
    f = _fact(db, m["id"], "date_of_birth")
    if f and DATE_RE.search(str(f[0].get("value"))):
        dob = Cited[str](value=DATE_RE.search(str(f[0]["value"])).group(0), citations=f[1])
    elif c and (raw := jload(c["raw"], {}) or {}).get("date_of_birth"):
        cit = record_citation(db, f"contact:{c['id']}", contains="Date of birth")
        if cit:
            dob = Cited[str](value=str(raw["date_of_birth"])[:10], citations=[cit])
    age = None
    if isinstance(dob, Cited):
        b = date.fromisoformat(dob.value[:10])
        t = date.today()
        age = t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    return ClientInfo(contact_id=c["id"] if c else None, name=name, photo_url=photo_url, photo_citation=photo_cit,
                      date_of_birth=dob, age=age, phone=c["phone"] if c else None, email=c["email"] if c else None)


def firm_spend(db: sqlite3.Connection, matter_id: int) -> Cited[float] | NotFound:
    rows = db.execute("SELECT * FROM records WHERE matter_id=? AND type='expense' AND deleted_at IS NULL "
                      "ORDER BY occurred_at", (matter_id,)).fetchall()
    total = sum((jload(r["meta"], {}) or {}).get("amount") or 0 for r in rows)
    if not rows:
        return NotFound(label="Firm expenses")
    return Cited[float](value=round(total, 2), citations=[record_citation(db, r["id"], rec=r) for r in rows][:25])


def costs(db: sqlite3.Connection, matter_id: int) -> Costs:
    rows = db.execute("SELECT * FROM records WHERE matter_id=? AND type='expense' AND deleted_at IS NULL",
                      (matter_id,)).fetchall()
    cats: dict[str, list] = {}
    months: dict[str, float] = {}
    for r in rows:
        meta = jload(r["meta"], {}) or {}
        amt = meta.get("amount") or 0
        cats.setdefault(meta.get("category") or "Other", []).append((amt, r))
        if r["occurred_at"]:
            months[r["occurred_at"][:7]] = months.get(r["occurred_at"][:7], 0) + amt
    by_cat = [CostCategory(category=k, amount=round(sum(a for a, _ in v), 2), count=len(v),
                           citations=[record_citation(db, r["id"], rec=r) for _, r in v][:10])
              for k, v in sorted(cats.items(), key=lambda kv: -sum(a for a, _ in kv[1]))]
    return Costs(total=firm_spend(db, matter_id), by_category=by_cat,
                 monthly=[MonthAmount(month=k, amount=round(v, 2)) for k, v in sorted(months.items())])


def deadlines(db: sqlite3.Connection, matter_id: int) -> Deadlines:
    now = today()
    overdue, upcoming, waiting = [], [], []
    for r in db.execute("SELECT * FROM records WHERE matter_id=? AND type='task' AND deleted_at IS NULL", (matter_id,)):
        meta = jload(r["meta"], {}) or {}
        if (meta.get("status") or "").lower() in ("complete", "completed", "done"):
            continue
        due = meta.get("due_at")
        item = DeadlineItem(id=r["id"], title=r["title"], kind="task", due_at=due, status=meta.get("status"),
                            assignee=meta.get("assignee"), overdue=bool(due and due[:10] < now),
                            citations=[record_citation(db, r["id"], rec=r)])
        (overdue if item.overdue else upcoming).append(item)
    for r in db.execute("SELECT * FROM records WHERE matter_id=? AND type='calendar_entry' AND deleted_at IS NULL "
                        "AND occurred_at >= ?", (matter_id, now)):
        upcoming.append(DeadlineItem(id=r["id"], title=r["title"], kind="calendar", due_at=r["occurred_at"],
                                     citations=[record_citation(db, r["id"], rec=r)]))
    sol = key_date(db, matter_id, "statute_of_limitations", "Statute of limitations", r"statute|limitation|\bSOL\b")
    if isinstance(sol, Cited):
        item = DeadlineItem(id="sol", title="Statute of limitations", kind="sol", due_at=sol.value,
                            overdue=sol.value < now, citations=sol.citations)
        (overdue if item.overdue else upcoming).append(item)
    seen = set()
    for r in db.execute("""SELECT r.*, d.waiting_on FROM digests d JOIN records r ON r.id=d.record_id
                           WHERE d.matter_id=? AND d.waiting_on IS NOT NULL AND d.waiting_on != ''
                             AND r.deleted_at IS NULL AND COALESCE(r.occurred_at,'') >= ?
                           ORDER BY r.occurred_at DESC""", (matter_id, _minus_days(now, 120))):
        meta = jload(r["meta"], {}) or {}
        if r["type"] == "task" and (meta.get("status") or "").lower() in ("complete", "completed", "done"):
            continue
        key = r["waiting_on"].split(":")[0].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        waiting.append(DeadlineItem(id=f"waiting:{r['id']}", title=r["waiting_on"], kind="waiting_on",
                                    waiting_on=r["waiting_on"].split(":")[0].strip(), due_at=r["occurred_at"],
                                    citations=[record_citation(db, r["id"], rec=r)]))
    for req in open_requests(db, matter_id):
        key = (req["provider_name"] or "").lower()
        if key in seen:
            continue
        seen.add(key)
        waiting.append(DeadlineItem(id=f"waiting:{req['id']}", title=f"{req['provider_name']}: {req['description']}",
                                    kind="waiting_on", waiting_on=req["provider_name"], due_at=req["requested_at"],
                                    citations=[Citation(**c) for c in req["citations"]]))
    overdue.sort(key=lambda d: d.due_at or "")
    upcoming.sort(key=lambda d: d.due_at or "9999")
    return Deadlines(overdue=overdue, upcoming=upcoming, waiting_on=waiting)


def _minus_days(d: str, n: int) -> str:
    from datetime import timedelta

    return (date.fromisoformat(d) - timedelta(days=n)).isoformat()


def open_requests(db: sqlite3.Connection, matter_id: int, provider_contact_id: int | None = None) -> list[dict]:
    rows = db.execute("""SELECT p.*, COALESCE(s.state,'open') AS state FROM provider_requests p
                         LEFT JOIN request_states s ON s.request_id = p.id
                         WHERE p.matter_id=? AND (? IS NULL OR p.provider_contact_id=?)""",
                      (matter_id, provider_contact_id, provider_contact_id)).fetchall()
    return [{**dict(r), "citations": jload(r["citations"], [])} for r in rows if r["state"] == "open"]


def timeline(db: sqlite3.Connection, matter_id: int, types: list[str] | None, since: str | None, q: str | None,
             limit: int) -> tuple[list[TimelineItem], int]:
    sql = ["""SELECT r.*, d.one_liner, d.category, d.importance FROM records r LEFT JOIN digests d ON d.record_id=r.id
              WHERE r.matter_id=? AND r.deleted_at IS NULL AND r.type != 'contact'"""]
    args: list = [matter_id]
    if types:
        sql.append(f"AND r.type IN ({','.join('?' * len(types))})")
        args += types
    if since:
        sql.append("AND r.last_changed_at > ?")
        args.append(since)
    if q:
        sql.append("AND (r.title LIKE ? OR r.body_text LIKE ? OR d.one_liner LIKE ?)")
        args += [f"%{q}%"] * 3
    rows = db.execute(" ".join(sql) + " ORDER BY COALESCE(r.occurred_at, r.first_seen_at) DESC", args).fetchall()
    items = [TimelineItem(record_id=r["id"], type=r["type"], title=r["title"] or r["type"],
                          occurred_at=r["occurred_at"], author=r["author"], one_liner=r["one_liner"],
                          category=r["category"], importance=r["importance"],
                          citations=[record_citation(db, r["id"], rec=r)]) for r in rows[:limit]]
    return items, len(rows)


def provider_summaries(db: sqlite3.Connection, matter_id: int) -> list[ProviderSummary]:
    provs = {r["id"]: r for r in db.execute(
        """SELECT c.*, mc.relationship FROM matter_contacts mc JOIN contacts c ON c.id=mc.contact_id
           WHERE mc.matter_id=? AND mc.role='medical_provider'""", (matter_id,))}
    bills: dict[int, list] = {}
    for r in db.execute("SELECT * FROM records WHERE matter_id=? AND type='medical_bill' AND deleted_at IS NULL",
                        (matter_id,)):
        meta = jload(r["meta"], {}) or {}
        pid = meta.get("provider_contact_id")
        if pid:
            bills.setdefault(pid, []).append((meta, r))
            if pid not in provs:
                c = db.execute("SELECT *, NULL AS relationship FROM contacts WHERE id=?", (pid,)).fetchone()
                if c:
                    provs[pid] = c
    visits: dict[int, list[Visit]] = {}
    for v, cits in [(jload(r["value"], {}), [Citation(**c) for c in jload(r["citations"], [])])
                    for r in db.execute("SELECT value, citations FROM facts WHERE matter_id=? AND kind='treatment_visit'",
                                        (matter_id,))]:
        if v.get("provider_contact_id") and v.get("date") and DATE_RE.match(v["date"]) and not v.get("missed"):
            visits.setdefault(v["provider_contact_id"], []).append(
                Visit(date=v["date"][:10], description=v.get("description"), citations=cits))
    for pid, items in bills.items():
        for meta, r in items:
            if meta.get("bill_date") and DATE_RE.match(str(meta["bill_date"])):
                visits.setdefault(pid, []).append(Visit(date=str(meta["bill_date"])[:10], description="Bill date",
                                                        citations=[record_citation(db, r["id"], rec=r)]))
    out = []
    for pid, c in provs.items():
        b = bills.get(pid, [])
        billed = sum(m.get("amount") or 0 for m, _ in b)
        bal_items = [(m, r) for m, r in b if m.get("balance") is not None]
        cits = [record_citation(db, r["id"], rec=r) for _, r in b]
        vs = sorted({v.date: v for v in visits.get(pid, [])}.values(), key=lambda v: v.date)
        gaps = [_days_between(a.date, b_.date) for a, b_ in zip(vs, vs[1:])]
        out.append(ProviderSummary(
            contact_id=pid, name=c["name"], email=c["email"], phone=c["phone"],
            relationship=c["relationship"] if "relationship" in c.keys() else None,
            billed=Cited[float](value=round(billed, 2), citations=cits) if b else NotFound(label="Billed amount"),
            balance=Cited[float](value=round(sum(m["balance"] for m, _ in bal_items), 2),
                                 citations=[record_citation(db, r["id"], rec=r) for _, r in bal_items])
            if bal_items else NotFound(label="Balance"),
            lien=any(m.get("lien") for m, _ in b), visits=vs,
            first_visit=vs[0].date if vs else None, last_visit=vs[-1].date if vs else None,
            current_gap_days=_days_between(vs[-1].date, today()) if vs else None,
            longest_gap_days=max(gaps) if gaps else None,
            open_requests=len(open_requests(db, matter_id, pid))))
    out.sort(key=lambda p: -(p.billed.value if isinstance(p.billed, Cited) else 0))
    return out


def overview(db: sqlite3.Connection, m: sqlite3.Row) -> Overview:
    from ..sync.engine import last_synced_at

    dl = deadlines(db, m["id"])
    nxt = next((d for d in dl.upcoming), None)
    med, med_cits = value.medical_specials(db, m["id"])
    last_run = db.execute("SELECT MAX(finished_at) FROM digest_runs WHERE matter_id=?", (m["id"],)).fetchone()[0]
    return Overview(
        matter=matter_summary(db, m), client=client_info(db, m), stage=stage_info(db, m),
        date_of_incident=key_date(db, m["id"], "date_of_incident", "Date of incident",
                                  r"incident|accident|date of loss|injury date|\bDOI\b|\bDOL\b"),
        statute_of_limitations=key_date(db, m["id"], "statute_of_limitations", "Statute of limitations",
                                        r"statute|limitation|\bSOL\b"),
        firm_spend=firm_spend(db, m["id"]),
        medical_specials=Cited[float](value=round(med, 2), citations=med_cits) if med_cits
        else NotFound(label="Medical specials"),
        next_deadline=nxt, last_client_contact=last_client_contact(db, m["id"]),
        last_synced_at=last_synced_at(db, m["id"]), last_digested_at=last_run)
