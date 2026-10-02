"use client";
import { fmtDateTime, usd } from "@/lib/format";
import type { AiCostReport, DigestRun } from "@/lib/types";
import { useApi } from "@/lib/use-api";

/** Quiet data-freshness line: when Clio was synced, when the AI last digested, and what it cost. */
export function CostPill({ matterId, lastSyncedAt }: { matterId: number; lastSyncedAt?: string | null }) {
  const runs = useApi<DigestRun[]>(`/api/matters/${matterId}/digest-runs`);
  const costs = useApi<AiCostReport>(`/api/ai-costs?matter_id=${matterId}`);
  const last = runs.data?.[0];   // newest first
  return (
    <p className="flex flex-wrap items-center justify-end gap-x-3 gap-y-1 text-xs text-muted-foreground">
      {lastSyncedAt && <span>Synced {fmtDateTime(lastSyncedAt)}</span>}
      {last && <span>Digested {fmtDateTime(last.finished_at ?? last.started_at)}</span>}
      {last?.cache_hit && <span className="inline-flex items-center gap-1 text-success"><span className="size-1.5 rounded-full bg-success" />cache hit</span>}
      {last && <span>{usd(last.cost_usd)} last run</span>}
      {costs.data && <span>case total {usd(costs.data.total_usd)}</span>}
    </p>
  );
}
