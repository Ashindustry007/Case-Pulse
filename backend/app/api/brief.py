"""[Dev 1] Brief (F2 key moments, F4 worth/coverage, story), F1 visits/changes/delta, suggested questions."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from ..ai import brief as B
from ..ai import value, views
from ..ai.background import refresh_on_open
from ..auth import require_role
from ..contracts import (Brief, ChangeItem, Changes, Citation, CitedSentence, Delta, Injury, KeyMoment, LastActivity,
                         SuggestedQuestions, VisitResponse)
from ..db import get_db, jload, now_iso
from ..rag.cite import record_citation
from ..sync.engine import fresh_enough
from .matters import get_matter

router = APIRouter(prefix="/api/matters", tags=["brief"])
attorney = require_role("attorney")
SESSION_MINUTES = 30
FIRST_VISIT_DAYS = 14


@router.get("/{matter_id}/brief", response_model=Brief, dependencies=[Depends(attorney)])
def brief(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    injuries = []
    for r in db.execute("SELECT value, citations FROM facts WHERE matter_id=? AND kind='injury'", (matter_id,)):
        v, cits = jload(r["value"], {}), [Citation(**c) for c in jload(r["citations"], [])]
        if cits:
            injuries.append(Injury(name=v.get("name") or "Injury", body_region=v.get("body_region"),
                                   severity_tier=v.get("severity_tier"), primary=bool(v.get("primary")),
                                   description=v.get("description"), citations=cits))
    injuries.sort(key=lambda i: not i.primary)
    last_run = db.execute("SELECT finished_at FROM digest_runs WHERE matter_id=? AND finished_at IS NOT NULL "
                          "ORDER BY id DESC LIMIT 1", (matter_id,)).fetchone()
    last_change = db.execute("SELECT MAX(last_changed_at) FROM records WHERE matter_id=?", (matter_id,)).fetchone()[0]
    cost = db.execute("SELECT COALESCE(SUM(cost_usd),0) FROM ai_runs WHERE matter_id=?", (matter_id,)).fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM records WHERE matter_id=? AND deleted_at IS NULL AND type != 'contact'",
                       (matter_id,)).fetchone()[0]
    return Brief(
        matter_id=matter_id,
        story=[CitedSentence(**s) for s in (B.latest(db, matter_id, "story") or [])],
        key_moments=[KeyMoment(**k) for k in (B.latest(db, matter_id, "key_moments") or [])],
        total_records=total, injuries=injuries, worth=value.worth(db, matter_id),
        coverage=value.coverage(db, matter_id), waiting_on=views.deadlines(db, matter_id).waiting_on,
        last_client_contact=views.last_client_contact(db, matter_id),
        digested_at=last_run["finished_at"] if last_run else None, cost_usd=round(cost, 4),
        stale=(last_run is None) or bool(last_change and last_change > last_run["finished_at"]))


@router.post("/{matter_id}/visits", response_model=VisitResponse)
def visit(matter_id: int, user=Depends(attorney), db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    synced = False
    if not fresh_enough(db, matter_id, minutes=2):
        db.commit()
        synced = refresh_on_open(matter_id)
    now = now_iso()
    last = db.execute("SELECT * FROM matter_visits WHERE user_id=? AND matter_id=? ORDER BY id DESC LIMIT 1",
                      (user["id"], matter_id)).fetchone()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=SESSION_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
    if last and last["last_seen_at"] >= cutoff:  # reload within the same session → same baseline
        db.execute("UPDATE matter_visits SET last_seen_at=? WHERE id=?", (now, last["id"]))
        vid, visited_at, prev = last["id"], last["visited_at"], last["previous_visit_at"]
    else:
        prev = last["last_seen_at"] if last else None
        cur = db.execute("""INSERT INTO matter_visits(user_id, matter_id, visited_at, last_seen_at, previous_visit_at)
                            VALUES (?,?,?,?,?)""", (user["id"], matter_id, now, now, prev))
        vid, visited_at = cur.lastrowid, now
    return VisitResponse(visit_id=vid, visited_at=visited_at, previous_visit_at=prev, first_visit=prev is None,
                         synced=synced)


def _fmt(ts: str) -> str:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%b %d, %H:%M")
    except ValueError:
        return ts


@router.get("/{matter_id}/changes", response_model=Changes, dependencies=[Depends(attorney)])
def changes(matter_id: int, since: str | None = None, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    since = since.replace(" ", "+") if since else None  # tolerate un-encoded "+00:00"
    first = since is None
    if first:
        floor = (datetime.now(timezone.utc) - timedelta(days=FIRST_VISIT_DAYS)).strftime("%Y-%m-%d")
        rows = db.execute("""SELECT r.*, d.importance, d.why_it_matters FROM records r
                             LEFT JOIN digests d ON d.record_id = r.id
                             WHERE r.matter_id=? AND r.type NOT IN ('contact') AND r.deleted_at IS NULL
                               AND COALESCE(r.occurred_at,'') >= ?""", (matter_id, floor)).fetchall()
    else:
        rows = db.execute("""SELECT r.*, d.importance, d.why_it_matters FROM records r
                             LEFT JOIN digests d ON d.record_id = r.id
                             WHERE r.matter_id=? AND r.type NOT IN ('contact')
                               AND (r.last_changed_at > ? OR COALESCE(r.deleted_at,'') > ?)""",
                          (matter_id, since, since)).fetchall()
    items = []
    for r in rows:
        if r["deleted_at"]:
            change = "removed"
        elif first or r["first_seen_at"] > since:
            change = "new"
        else:
            change = "changed"
        cit = record_citation(db, r["id"], rec=r)
        if cit:
            items.append(ChangeItem(record_id=r["id"], change=change, type=r["type"], title=r["title"] or r["type"],
                                    occurred_at=r["occurred_at"], importance=r["importance"],
                                    why_it_matters=r["why_it_matters"], citations=[cit]))
    items.sort(key=lambda i: (-(i.importance or 0), i.occurred_at or ""), reverse=False)
    la_row = db.execute("""SELECT * FROM records WHERE matter_id=? AND deleted_at IS NULL AND occurred_at IS NOT NULL
                           AND type NOT IN ('contact','custom_field') AND occurred_at <= ?
                           ORDER BY occurred_at DESC LIMIT 1""", (matter_id, now_iso())).fetchone()
    last_activity = None
    if la_row and (c := record_citation(db, la_row["id"], rec=la_row)):
        who = f" by {la_row['author']}" if la_row["author"] else ""
        last_activity = LastActivity(at=la_row["occurred_at"],
                                     description=f"{la_row['type'].replace('_', ' ')} “{la_row['title']}”{who}",
                                     citations=[c])
    empty = None
    if not items:
        tail = f" Last activity on the case: {last_activity.at[:10]}, {last_activity.description}." if last_activity else ""
        empty = (f"Nothing has changed since your last visit ({_fmt(since)})." if not first
                 else f"No activity in the last {FIRST_VISIT_DAYS} days.") + tail
    return Changes(since=since, first_visit=first, items=items, empty_message=empty, last_activity=last_activity)


@router.get("/{matter_id}/delta", response_model=Delta, dependencies=[Depends(attorney)])
def delta(matter_id: int, since: str | None = None, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    since = since.replace(" ", "+") if since else None
    if since is None:
        since = (datetime.now(timezone.utc) - timedelta(days=FIRST_VISIT_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        summary, cached = B.delta(db, matter_id, since)
    except Exception:  # noqa: BLE001 — summary is optional; the item list (/changes) is the source of truth
        summary, cached = [], False
    return Delta(since=since, summary=[CitedSentence(**s) for s in summary], cached=cached)


@router.get("/{matter_id}/suggested-questions", response_model=SuggestedQuestions, dependencies=[Depends(attorney)])
def suggested_questions(matter_id: int, db: sqlite3.Connection = Depends(get_db)):
    get_matter(db, matter_id)
    try:
        qs = B.suggested_questions(db, matter_id)
    except Exception:  # noqa: BLE001
        qs = []
    return SuggestedQuestions(questions=qs or ["What are the client's primary injuries?",
                                               "What insurance coverage is behind this case?",
                                               "What are we waiting on right now?",
                                               "When did we last talk to the client?"])
