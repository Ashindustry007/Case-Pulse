"""Clio item → normalized, citable record.

Each renderer returns a `Rendered` whose `body_text` is the human-readable text that citations index into.
Structured items (bills, expenses, tasks...) render one fact per line so a citation excerpt is a clean line.
Nothing here is case-specific: only generic Clio field names and generic PI vocabulary.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Any

PROVIDER_WORDS = ("medical", "physician", "doctor", "dr.", "chiropract", "therap", "hospital", "clinic", "ortho",
                  "radiolog", "imaging", "mri", "pharmac", "rehab", "emergency", "urgent care", "surgeon", "surgery",
                  "pain", "neuro", "health", "provider", "treating", "medicine", "ambulance", "physical", "spine")
INSURER_WORDS = ("insur", "adjuster", "carrier", "claims", "underwrit", "casualty", "mutual", "indemnity")
ATTORNEY_WORDS = ("attorney", "counsel", "law firm", "lawyer", "defense", "esq")


@dataclass
class Rendered:
    title: str
    body_text: str
    occurred_at: str | None = None
    author: str | None = None
    participants: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


def file_ext(name: str | None, content_type: str | None) -> str:
    """Stable file extension for a downloaded document (title first, then content type)."""
    m = re.search(r"\.([A-Za-z0-9]{1,5})$", name or "")
    if m:
        return m.group(1).lower()
    return {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg", "text/plain": "txt",
            "text/html": "html"}.get((content_type or "").split(";")[0].strip().lower(), "bin")


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>|</tr>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n\s*\n+", "\n\n", t)
    return t.strip()


def money(v: Any) -> str | None:
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return None


def name_of(obj: Any) -> str | None:
    if isinstance(obj, dict):
        return obj.get("name") or obj.get("option") or obj.get("description")
    return None


def _lines(*pairs: tuple[str, Any]) -> list[str]:
    return [f"{k}: {v}" for k, v in pairs if v not in (None, "", [], {})]


def classify_role(*texts: str | None) -> str:
    t = " ".join(x for x in texts if x).lower()
    if not t:
        return "other"
    if any(w in t for w in INSURER_WORDS):
        return "insurer"
    if any(w in t for w in PROVIDER_WORDS):
        return "medical_provider"
    if any(w in t for w in ATTORNEY_WORDS):
        return "attorney"
    return "other"


def cf_value(cfv: dict) -> str | None:
    v = cfv.get("value")
    po = cfv.get("picklist_option")
    if isinstance(po, dict) and po.get("option"):
        return str(po["option"])
    if isinstance(v, dict):
        return name_of(v) or str(v.get("id"))
    if v in (None, ""):
        return None
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if cfv.get("field_type") == "currency":
        return money(v) or str(v)
    return str(v)


# ------------------------------------------------------------------------------------------------------------------
def note(n: dict) -> Rendered:
    subject = n.get("subject") or "Note"
    detail = strip_html(n.get("detail"))
    author = name_of(n.get("author"))
    date = n.get("date") or n.get("created_at")
    body = "\n".join([f"Note: {subject}", *_lines(("Date", date), ("Author", author)), "", detail]).strip()
    return Rendered(title=subject, body_text=body, occurred_at=date, author=author)


def communication(c: dict) -> Rendered:
    subject = c.get("subject") or ("Phone call" if "Phone" in (c.get("type") or "") else "Message")
    senders = [{"name": name_of(s), "id": s.get("id"), "kind": s.get("type")} for s in c.get("senders") or []]
    receivers = [{"name": name_of(s), "id": s.get("id"), "kind": s.get("type")} for s in c.get("receivers") or []]
    kind = (c.get("type") or "Communication").replace("Communication", "") or "Message"
    date = c.get("date") or c.get("received_at") or c.get("created_at")
    head = _lines(("Type", kind), ("Date", date),
                  ("From", ", ".join(filter(None, (s["name"] for s in senders)))),
                  ("To", ", ".join(filter(None, (s["name"] for s in receivers)))))
    body = "\n".join([f"Subject: {subject}", *head, "", strip_html(c.get("body"))]).strip()
    parts = [{**s, "direction": "from"} for s in senders] + [{**r, "direction": "to"} for r in receivers]
    author = senders[0]["name"] if senders else name_of(c.get("user"))
    return Rendered(title=subject, body_text=body, occurred_at=date, author=author, participants=parts,
                    meta={"channel": kind.lower() or "message"})


def task(t: dict) -> Rendered:
    name = t.get("name") or "Task"
    assignee = name_of(t.get("assignee"))
    head = _lines(("Status", t.get("status")), ("Priority", t.get("priority")), ("Due", t.get("due_at")),
                  ("Completed", t.get("completed_at")), ("Assignee", assignee),
                  ("Assigned by", name_of(t.get("assigner"))), ("Task type", name_of(t.get("task_type"))))
    body = "\n".join([f"Task: {name}", *head, "", strip_html(t.get("description"))]).strip()
    return Rendered(title=name, body_text=body, occurred_at=t.get("due_at") or t.get("created_at"),
                    author=name_of(t.get("assigner")),
                    participants=[{"name": assignee, "id": (t.get("assignee") or {}).get("id"),
                                   "kind": (t.get("assignee") or {}).get("type"), "direction": "assignee"}],
                    meta={"status": t.get("status"), "due_at": t.get("due_at"), "completed_at": t.get("completed_at"),
                          "assignee": assignee, "assignee_kind": (t.get("assignee") or {}).get("type")})


def calendar_entry(e: dict) -> Rendered:
    summary = e.get("summary") or "Calendar entry"
    when = e.get("start_at")
    if e.get("end_at") and e.get("end_at") != when:
        when = f"{when} – {e.get('end_at')}"
    head = _lines(("When", when), ("All day", "Yes" if e.get("all_day") else None), ("Location", e.get("location")),
                  ("Owner", name_of(e.get("calendar_owner"))),
                  ("Attendees", ", ".join(filter(None, (name_of(a) for a in e.get("attendees") or [])))))
    body = "\n".join([f"Event: {summary}", *head, "", strip_html(e.get("description"))]).strip()
    return Rendered(title=summary, body_text=body, occurred_at=e.get("start_at"), author=name_of(e.get("calendar_owner")),
                    meta={"start_at": e.get("start_at"), "end_at": e.get("end_at")})


def document(d: dict) -> Rendered:
    name = d.get("name") or "Document"
    ver = d.get("latest_document_version") or {}
    head = _lines(("Category", name_of(d.get("document_category"))), ("Folder", name_of(d.get("parent"))),
                  ("Received", d.get("received_at")), ("Uploaded", d.get("created_at")),
                  ("Content type", d.get("content_type") or ver.get("content_type")))
    body = "\n".join([f"Document: {name}", *head]).strip()
    return Rendered(title=name, body_text=body, occurred_at=d.get("received_at") or d.get("created_at"),
                    author=name_of(d.get("creator")),
                    meta={"file_path": f"files/{d.get('id')}.{file_ext(name, d.get('content_type') or ver.get('content_type'))}",
                          "content_type": d.get("content_type") or ver.get("content_type"),
                          "size": d.get("size") or ver.get("size"), "version_id": ver.get("id"),
                          "category": name_of(d.get("document_category")), "folder": name_of(d.get("parent"))})


def activity(a: dict) -> tuple[str, Rendered]:
    is_expense = "Expense" in (a.get("type") or "")
    kind = "expense" if is_expense else "time_entry"
    note_prefix = (strip_html(a.get("note")).split(":", 1)[0].strip() if ":" in (a.get("note") or "") else "")[:60]
    label = name_of(a.get("expense_category")) or name_of(a.get("activity_description")) or note_prefix or (
        "Expense" if is_expense else "Time entry")
    total = a.get("total") if a.get("total") is not None else (
        (a.get("price") or 0) * (a.get("quantity") or 0) if is_expense else None)
    first = f"{'Expense' if is_expense else 'Time entry'} · {label} · {money(total) or ''} · {a.get('date') or ''}".strip(" ·")
    head = _lines(("Quantity", a.get("quantity")), ("Rate/price", money(a.get("price"))), ("By", name_of(a.get("user"))),
                  ("Reference", a.get("reference")))
    body = "\n".join([first, *head, "", strip_html(a.get("note"))]).strip()
    return kind, Rendered(title=label, body_text=body, occurred_at=a.get("date"), author=name_of(a.get("user")),
                          meta={"amount": float(total) if total is not None else None, "category": label,
                                "kind": a.get("type")})


def bill(b: dict) -> Rendered:
    num = b.get("number") or b.get("id")
    first = f"Bill #{num} · total {money(b.get('total')) or '?'} · balance {money(b.get('balance')) or '?'} · issued {b.get('issued_at') or '?'}"
    body = "\n".join([first, *_lines(("State", b.get("state")), ("Due", b.get("due_at")), ("Subject", b.get("subject")))])
    return Rendered(title=f"Bill #{num}", body_text=body, occurred_at=b.get("issued_at") or b.get("created_at"),
                    meta={"total": b.get("total"), "balance": b.get("balance"), "state": b.get("state")})


def medical_record(m: dict, provider_name: str | None) -> Rendered:
    prov = provider_name or name_of(m.get("medical_provider")) or "Medical provider"
    first = f"Medical records · {prov}"
    head = _lines(("Description", m.get("description")),
                  ("Treatment start", m.get("treatment_start_date")), ("Treatment end", m.get("treatment_end_date")),
                  ("In treatment", m.get("in_treatment")), ("Records status", m.get("record_status")),
                  ("Records requested", m.get("record_request_date")), ("Bills status", m.get("bill_status")),
                  ("Bills requested", m.get("bill_request_date")))
    body = "\n".join([first, *head])
    return Rendered(title=f"Medical records · {prov}", body_text=body,
                    occurred_at=m.get("treatment_start_date") or m.get("created_at"),
                    meta={"provider_contact_id": (m.get("medical_provider") or {}).get("id"), "provider_name": prov,
                          "treatment_start_date": m.get("treatment_start_date"),
                          "treatment_end_date": m.get("treatment_end_date"), "record_status": m.get("record_status"),
                          "bill_status": m.get("bill_status"), "record_request_date": m.get("record_request_date")})


def medical_bill(b: dict, provider_name: str | None, provider_id: int | None) -> Rendered:
    prov = provider_name or "Medical provider"
    lien = b.get("mark_balance_as_lien")
    first = f"Medical bill · {prov} · {money(b.get('amount')) or '?'} · {b.get('bill_date') or ''}".strip(" ·")
    payers = []
    for p in b.get("payers") or []:
        payers.append(f"{name_of(p.get('holder')) or 'Payer'} paid {money(p.get('amount')) or '?'}"
                      + (" (lien)" if p.get("mark_as_lien") else ""))
    head = _lines(("Bill name", b.get("name")), ("Received", b.get("bill_received_date")),
                  ("Adjustment", money(b.get("adjustment"))), ("Balance", money(b.get("balance"))),
                  ("Balance marked as lien", "Yes" if lien else ("No" if lien is False else None)),
                  ("Payers", "; ".join(payers)))
    body = "\n".join([first, *head])
    return Rendered(title=f"Medical bill · {prov}", body_text=body, occurred_at=b.get("bill_date"),
                    meta={"amount": _f(b.get("amount")), "balance": _f(b.get("balance")),
                          "adjustment": _f(b.get("adjustment")), "lien": bool(lien),
                          "provider_contact_id": provider_id, "provider_name": prov, "bill_date": b.get("bill_date")})


def damage(d: dict) -> Rendered:
    first = f"Damage · {d.get('damage_type') or 'other'} · {money(d.get('amount')) or '?'}"
    body = "\n".join([first, *_lines(("Description", d.get("description")))])
    return Rendered(title=f"Damage · {d.get('description') or d.get('damage_type') or ''}".strip(" ·"), body_text=body,
                    occurred_at=d.get("created_at"),
                    meta={"amount": _f(d.get("amount")), "damage_type": d.get("damage_type")})


def custom_field(cfv: dict) -> Rendered | None:
    val = cf_value(cfv)
    if val is None:
        return None
    fname = cfv.get("field_name") or "Custom field"
    return Rendered(title=f"Custom field · {fname}", body_text=f"{fname}: {val}",
                    meta={"field_name": fname, "field_type": cfv.get("field_type"), "value": val})


def contact(c: dict, relationship: str | None, role: str) -> Rendered:
    name = c.get("name") or " ".join(filter(None, [c.get("first_name"), c.get("last_name")])) or "Contact"
    emails = [e.get("address") for e in c.get("email_addresses") or [] if e.get("address")]
    phones = [p.get("number") for p in c.get("phone_numbers") or [] if p.get("number")]
    prim_email = c.get("primary_email_address") or (emails[0] if emails else None)
    prim_phone = c.get("primary_phone_number") or (phones[0] if phones else None)
    lines = [f"Contact: {name}", *_lines(("Relationship to matter", relationship), ("Type", c.get("type")),
                                         ("Title", c.get("title")), ("Company", name_of(c.get("company"))),
                                         ("Date of birth", c.get("date_of_birth")), ("Email", prim_email),
                                         ("Phone", prim_phone))]
    for cfv in c.get("custom_field_values") or []:
        v = cf_value(cfv)
        if v is not None:
            lines.append(f"{cfv.get('field_name')}: {v}")
    return Rendered(title=f"Contact · {name}", body_text="\n".join(lines),
                    meta={"contact_id": c.get("id"), "name": name, "email": prim_email, "phone": prim_phone,
                          "date_of_birth": c.get("date_of_birth"), "relationship": relationship, "role": role})


def _f(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
