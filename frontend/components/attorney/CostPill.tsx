"use client";
import { fmtDateTime, usd } from "@/lib/format";
import type { AiCostReport, DigestRun } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function CostPill({ matterId, lastSyncedAt }: { matterId: number; lastSyncedAt?: string | null }) {
  const runs = useApi<DigestRun[]>(`/api/matters/${matterId}/digest-runs`);
  const costs = useApi<AiCostReport>(`/api/ai-costs?matter_id=${matterId}`);
  const last = runs.data?.at(-1);
  return (
    <span className="inline-flex flex-wrap items-center gap-1 rounded-full border px-3 py-0.5 text-xs text-muted-foreground">
      {lastSyncedAt && <span>Synced {fmtDateTime(lastSyncedAt)}</span>}
      {last && <span>· Digested {fmtDateTime(last.finished_at ?? last.started_at)}</span>}
      {last?.cache_hit && <span className="font-medium text-emerald-700 dark:text-emerald-400">· cache hit</span>}
      {last && <span>· {usd(last.cost_usd)}</span>}
      {costs.data && <span>(case {usd(costs.data.total_usd)})</span>}
    </span>
  );
}
