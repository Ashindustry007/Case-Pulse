"""[Dev 1] AI cost monitoring for attorneys (F10). Source of truth: ai_runs (every Claude call + cache hits)."""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from ..auth import require_role
from ..config import settings
from ..contracts import AiCostReport, AiRun, DayCost, FirmCostReport, MatterCost, PurposeCost
from ..db import get_db

router = APIRouter(prefix="/api/ai-costs", tags=["costs"], dependencies=[Depends(require_role("attorney"))])
ONGOING = ("ask", "locate", "draft", "classify", "delta")


@router.get("", response_model=AiCostReport)
def matter_costs(matter_id: int | None = None, date_from: str | None = None, date_to: str | None = None,
                 db: sqlite3.Connection = Depends(get_db)):
    where = ["(? IS NULL OR a.matter_id = ?)", "a.created_at >= ?", "a.created_at <= ?"]
    args = [matter_id, matter_id, date_from or "", (date_to or "9999") + "~"]
    w = " AND ".join(where)
    rows = db.execute(f"""SELECT a.*, u.name AS user_name FROM ai_runs a LEFT JOIN users u ON u.id = a.user_id
                          WHERE {w} ORDER BY a.id DESC""", args).fetchall()
    paid = [r for r in rows if not r["cache_hit"]]
    total = sum(r["cost_usd"] for r in paid)
    ongoing = sum(r["cost_usd"] for r in paid if r["purpose"] in ONGOING)
    asks = [r for r in paid if r["purpose"] == "ask"]

    def group(key: str) -> list[PurposeCost]:
        g: dict[str, list] = {}
        for r in paid:
            g.setdefault(r[key], []).append(r["cost_usd"])
        return sorted((PurposeCost(key=k, usd=round(sum(v), 4), calls=len(v)) for k, v in g.items()),
                      key=lambda p: -p.usd)

    days: dict[str, float] = {}
    for r in paid:
        days[r["created_at"][:10]] = days.get(r["created_at"][:10], 0) + r["cost_usd"]
    budget = None
    if matter_id is not None:
        b = db.execute("SELECT budget_usd FROM matter_budgets WHERE matter_id=?", (matter_id,)).fetchone()
        budget = b["budget_usd"] if b else settings.ai_budget_per_matter_usd
    return AiCostReport(
        matter_id=matter_id, total_usd=round(total, 4), one_time_usd=round(total - ongoing, 4),
        ongoing_usd=round(ongoing, 4), ask_count=len(asks),
        avg_ask_usd=round(sum(r["cost_usd"] for r in asks) / len(asks), 4) if asks else 0.0,
        cache_savings_usd=round(sum(r["saved_usd"] for r in rows if r["cache_hit"]), 4),
        by_purpose=group("purpose"), by_model=group("model"),
        series=[DayCost(date=d, usd=round(v, 4)) for d, v in sorted(days.items())],
        budget_usd=budget, budget_pct=round(100 * total / budget, 1) if budget else None,
        runs=[AiRun(at=r["created_at"], user=r["user_name"], purpose=r["purpose"], model=r["model"],
                    input_tokens=r["input_tokens"], output_tokens=r["output_tokens"], cost_usd=round(r["cost_usd"], 5),
                    cache_hit=bool(r["cache_hit"])) for r in rows[:100]])


@router.get("/firm", response_model=FirmCostReport)
def firm_costs(days: int = 30, db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("""SELECT a.matter_id, m.display_number, m.description, SUM(a.cost_usd) AS usd FROM ai_runs a
                         LEFT JOIN matters m ON m.id = a.matter_id WHERE a.cache_hit = 0 AND a.matter_id IS NOT NULL
                         GROUP BY a.matter_id ORDER BY usd DESC""").fetchall()
    series = db.execute("""SELECT substr(created_at,1,10) AS d, SUM(cost_usd) AS usd FROM ai_runs WHERE cache_hit=0
                           AND created_at >= date('now', ?) GROUP BY d ORDER BY d""", (f"-{days} days",)).fetchall()
    return FirmCostReport(matters=[MatterCost(matter_id=r["matter_id"], display_number=r["display_number"],
                                              description=r["description"], total_usd=round(r["usd"], 4))
                                   for r in rows],
                          series=[DayCost(date=r["d"], usd=round(r["usd"], 4)) for r in series],
                          total_usd=round(sum(r["usd"] for r in rows), 4))
