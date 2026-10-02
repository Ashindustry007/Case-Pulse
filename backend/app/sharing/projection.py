"""[Dev 2] ProviderProjection: the ONLY code path that produces provider-visible data.

build_sections() computes everything one provider COULD see (already scoped to them). project() is a whitelist that
starts from the identity fields and copies a section only if the policy grants it. Share-candidates is project() with
every field granted, so the composer preview and the real provider page come from the same code.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import get_args

from ..config import settings
from ..contracts import (Adherence, CaseValueShare, Coverage, CoverageShare, Heartbeat, HeartbeatState, Movement,
                         OtherCare, ProviderBills, ProviderCase, ProviderRequest, SharedDocument, ShareField,
                         SharePolicy)
from ..db import now_iso
from . import requests, sources

ALL_FIELDS: list[str] = list(get_args(ShareField))
ACTIVE_DAYS, QUIET_DAYS, GAP_DAYS = 30, 90, 30


def heartbeat_state(matter_status: str | None, last_activity_at: str | None, today: date) -> HeartbeatState:
    if (matter_status or "").lower() == "closed":
        return "closed"
    if not last_activity_at:
        return "dormant"
    days = (today - date.fromisoformat(last_activity_at[:10])).days
    return "active" if days <= ACTIVE_DAYS else "quiet" if days <= QUIET_DAYS else "dormant"


@dataclass
class Sections:
    patient_display: str
    heartbeat: Heartbeat
    coverage_variants: dict[str, CoverageShare]
    case_value: CaseValueShare | None
    bills: ProviderBills | None
    requests: list[ProviderRequest]
    documents: list[SharedDocument]
    adherence: Adherence | None
    other_care: list[OtherCare]


def build_sections(db: sqlite3.Connection, matter_id: int, provider_contact_id: int) -> Sections:
    now = now_iso()
    today = date.fromisoformat(now[:10])
    m = sources.matter(db, matter_id)
    last = sources.last_activity_at(db, matter_id, now)
    moves = sources.movements(db, matter_id, now)
    last_move = moves[0] if moves else None
    if last and (last_move is None or last[:10] > last_move.date):
        last_move = Movement(date=last[:10], text="Case activity recorded")  # newest event is not provider-safe
    worth = sources.worth(db, matter_id)
    visits = sources.treatment_visits(db, matter_id)
    return Sections(
        patient_display=sources.patient_display(db, matter_id),
        heartbeat=Heartbeat(state=heartbeat_state(m["status"] if m else None, last, today),
                            last_activity_at=last[:10] if last else None, last_movement=last_move,
                            stage=sources.stage(db, matter_id), recent_movement=moves),
        coverage_variants=_coverage_variants(sources.coverage(db, matter_id)),
        case_value=CaseValueShare(low=worth.low, high=worth.high) if worth else None,
        bills=sources.provider_bills(db, matter_id, provider_contact_id),
        requests=requests.requests_for(db, matter_id, provider_contact_id, audience="provider"),
        documents=sources.documents(db, matter_id),
        adherence=_adherence(visits, provider_contact_id, today),
        other_care=_other_care(visits, provider_contact_id),
    )


def project(s: Sections, *, grant_id: int, policy: SharePolicy, shared_by: str | None) -> ProviderCase:
    granted = set(policy.fields)
    out: dict = dict(grant_id=grant_id, policy_version=policy.version, patient_display=s.patient_display,
                     firm_name=settings.firm_name, shared_by=shared_by, updated_at=policy.released_at,
                     status_note=policy.status_note or None)
    if "status" in granted:
        out["heartbeat"] = s.heartbeat
    if "coverage" in granted:
        out["coverage"] = s.coverage_variants.get(policy.coverage_detail)
    if "case_value" in granted:
        out["case_value"] = s.case_value
    if "bills" in granted:
        out["bills"] = s.bills
    if "open_requests" in granted:
        out["requests"] = [r for r in s.requests if r.state != "dismissed"]
    if "documents" in granted:
        allowed = set(policy.document_ids)
        out["documents"] = [d.model_copy(update={"shared_at": policy.released_at}) for d in s.documents
                            if d.id in allowed]
    if "adherence" in granted:
        out["adherence"] = s.adherence
    if "other_care" in granted:
        out["other_care"] = s.other_care or None
    return ProviderCase(**out)


def preview_policy(grant_id: int, documents: list[SharedDocument]) -> SharePolicy:
    """Everything granted: share-candidates uses it so the composer can filter the same projection client-side."""
    return SharePolicy(grant_id=grant_id, version=0, fields=ALL_FIELDS, document_ids=[d.id for d in documents],
                       coverage_detail="limits", released_at=now_iso())


def _coverage_variants(cov: Coverage | None) -> dict[str, CoverageShare]:
    if cov is None:
        return {}
    found = [(label, getattr(f, "value", None)) for label, f in (
        ("BI per person", cov.bi_per_person), ("BI per accident", cov.bi_per_accident),
        ("UM/UIM", cov.um_uim), ("MedPay", cov.medpay))]
    return {"confirmed": CoverageShare(confirmed=cov.confirmed),
            "limits": CoverageShare(confirmed=cov.confirmed, carrier=getattr(cov.carrier, "value", None),
                                    limits_text=" · ".join(f"{label} {v}" for label, v in found if v) or None)}


def _adherence(visits: list[dict], contact_id: int, today: date) -> Adherence | None:
    dates = sorted({v["date"][:10] for v in visits if v.get("provider_contact_id") == contact_id})
    if not dates:
        return None
    ds = [date.fromisoformat(d) for d in dates]
    gaps = [{"from": a.isoformat(), "to": b.isoformat(), "days": (b - a).days}
            for a, b in zip(ds, ds[1:]) if (b - a).days > GAP_DAYS]
    return Adherence(visits=dates, gaps=gaps, current_gap_days=(today - ds[-1]).days)


def _other_care(visits: list[dict], contact_id: int) -> list[OtherCare]:
    by_name: dict[str, list[str]] = {}
    for v in visits:
        if v.get("provider_contact_id") != contact_id and v.get("provider_name"):
            by_name.setdefault(v["provider_name"], []).append(v["date"][:10])
    return [OtherCare(provider_name=n, first_visit=min(d), last_visit=max(d)) for n, d in sorted(by_name.items())]
