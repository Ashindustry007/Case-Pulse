"use client";
import Link from "next/link";
import { ErrorNote, Loading } from "@/components/common/states";
import { movedAgo } from "@/components/provider/ProviderCaseView";
import type { ProviderCaseSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function ProviderCases() {
  const { data, error, loading } = useApi<ProviderCaseSummary[]>("/api/provider/cases");
  return (
    <div className="space-y-3">
      <h1 className="text-lg font-semibold">Your shared cases</h1>
      <ErrorNote error={error} />
      {loading ? <Loading /> : data?.length === 0 ? <p className="text-muted-foreground">No cases are shared with you right now.</p> : (
        <ul className="divide-y rounded border bg-background">
          {data?.map((c) => (
            <li key={c.grant_id}>
              <Link href={`/provider/cases/${c.grant_id}`} className="flex flex-wrap items-center gap-2 p-3 hover:bg-muted/50">
                <span className="font-medium">{c.patient_display}</span>
                {c.state && <span className="text-sm">● {c.state}</span>}
                <span className="text-sm text-muted-foreground">{movedAgo(c.last_movement_at)}</span>
                {c.open_requests > 0 && <span className="text-sm">{c.open_requests} request{c.open_requests > 1 ? "s" : ""} for you</span>}
                <span className="ml-auto text-sm underline">Open</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
