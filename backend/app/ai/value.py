"""F4 — deterministic worth range + coverage tile from CITED inputs (bills, injuries, limits)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import yaml

from ..contracts import Assumption, Citation, Cited, Coverage, NotFound, WorthEstimate
from ..db import jload
from ..rag.cite import record_citation

MODEL = yaml.safe_load((Path(__file__).with_name("value_model.yaml")).read_text())
TIER_ORDER = ["soft_tissue", "objective", "surgical"]


def _money(v: float) -> str:
    return f"${v:,.0f}"


def _round(v: float) -> float:
    step = MODEL.get("round_to", 1000)
    return float(round(v / step) * step)


def parse_amount(text: str | None) -> float | None:
    if not text:
        return None
    m = re.search(r"\$?\s*([\d,]+(?:\.\d+)?)\s*(k|K|m|M|million)?", text)
    if not m:
        return None
    v = float(m.group(1).replace(",", ""))
    suf = (m.group(2) or "").lower()
    return v * (1000 if suf == "k" else 1_000_000 if suf in ("m", "million") else 1)


def medical_specials(db: sqlite3.Connection, matter_id: int) -> tuple[float, list[Citation]]:
    total, cits = 0.0, []
    for r in db.execute("""SELECT * FROM records WHERE matter_id=? AND type='medical_bill' AND deleted_at IS NULL
                           ORDER BY occurred_at""", (matter_id,)):
        amt = (jload(r["meta"], {}) or {}).get("amount")
        if amt:
            total += float(amt)
            if (c := record_citation(db, r["id"], rec=r)):
                cits.append(c)
    return total, cits


def special_damages(db: sqlite3.Connection, matter_id: int) -> tuple[float, list[Citation]]:
    total, cits = 0.0, []
    for r in db.execute("""SELECT * FROM records WHERE matter_id=? AND type='damage' AND deleted_at IS NULL""",
                        (matter_id,)):
        meta = jload(r["meta"], {}) or {}
        if meta.get("amount") and (meta.get("damage_type") or "").lower() in ("special", "special_damages", "specials"):
            total += float(meta["amount"])
            if (c := record_citation(db, r["id"], rec=r)):
                cits.append(c)
    return total, cits


def _facts(db: sqlite3.Connection, matter_id: int, kind: str) -> list[tuple[dict, list[Citation]]]:
    return [(jload(r["value"], {}), [Citation(**c) for c in jload(r["citations"], [])])
            for r in db.execute("SELECT value, citations FROM facts WHERE matter_id=? AND kind=?", (matter_id, kind))]


def coverage(db: sqlite3.Connection, matter_id: int) -> Coverage:
    found = {v["field"]: Cited[str](value=v["value"], citations=c) for v, c in _facts(db, matter_id, "coverage") if c}
    labels = {"carrier": "Liability carrier", "bi_per_person": "BI limit per person",
              "bi_per_accident": "BI limit per accident", "um_uim": "UM/UIM limits", "medpay": "MedPay / PIP"}
    vals = {f: found.get(f) or NotFound(label=labels[f]) for f in labels}
    return Coverage(**vals, confirmed=any(f in found for f in ("carrier", "bi_per_person", "bi_per_accident")))


def worth(db: sqlite3.Connection, matter_id: int) -> WorthEstimate | NotFound:
    med, med_cits = medical_specials(db, matter_id)
    dmg, dmg_cits = special_damages(db, matter_id)
    if med <= 0:
        return NotFound(label="Medical specials (no medical bills found in file)")
    injuries = _facts(db, matter_id, "injury")
    tier, tier_cits, tier_name = None, [], None
    for v, cits in injuries:
        t = v.get("severity_tier")
        if t in TIER_ORDER and (tier is None or TIER_ORDER.index(t) > TIER_ORDER.index(tier)):
            tier, tier_cits, tier_name = t, cits, v.get("name")
    band = MODEL["tiers"][tier or MODEL["default_tier_when_unknown"]]
    low = _round(med * band["low"] + dmg)
    high = _round(med * band["high"] + dmg)
    assumptions = [Assumption(label="Bills total", text=f"{_money(med)} in medical bills ({len(med_cits)} bills)",
                              citations=med_cits)]
    if tier:
        assumptions.append(Assumption(label="Injury severity",
                                      text=f"{band['label']}: {tier_name} → ×{band['low']}–{band['high']}",
                                      citations=tier_cits[:3]))
    else:
        assumptions.append(Assumption(label="Injury severity", not_found=True,
                                      text=f"Not found in file — lowest band applied (×{band['low']}–{band['high']})"))
    if dmg > 0:
        assumptions.append(Assumption(label="Other special damages", text=f"{_money(dmg)} added 1:1",
                                      citations=dmg_cits))
    cov = coverage(db, matter_id)
    cap_note = None
    if isinstance(cov.bi_per_person, Cited):
        limit = parse_amount(cov.bi_per_person.value)
        assumptions.append(Assumption(label="Policy limits", text=f"BI {cov.bi_per_person.value} per person",
                                      citations=cov.bi_per_person.citations))
        if limit and high > limit:
            cap_note = f"Recovery may be capped by available coverage of {_money(limit)} per person."
    else:
        assumptions.append(Assumption(label="Policy limits", not_found=True, text="Not found in file"))
    return WorthEstimate(low=low, high=high, assumptions=assumptions, cap_note=cap_note,
                         method=" ".join(MODEL["method"].split()))
