"use client";
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import { ErrorNote, Loading } from "@/components/common/states";
import { movedAgo } from "@/components/provider/ProviderCaseView";
import type { ProviderCaseSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const DOT: Record<string, string> = { active: "bg-success", quiet: "bg-warning", dormant: "bg-muted-foreground", closed: "bg-muted-foreground/60" };

export default function ProviderCases() {
  const { data, error, loading } = useApi<ProviderCaseSummary[]>("/api/provider/cases");
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Your shared cases</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">Only what each firm has chosen to share with you.</p>
      </div>
      <ErrorNote error={error} />
      {loading ? <Loading lines={3} /> : data?.length === 0 ? <p className="text-muted-foreground">No cases are shared with you right now.</p> : (
        <ul className="space-y-3">
          {data?.map((c) => (
            <li key={c.grant_id}>
              <Link href={`/provider/cases/${c.grant_id}`} className="group flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border bg-card px-5 py-4 transition-colors hover:border-primary/50 hover:bg-accent/30">
                <span className="text-[15px] font-medium">Patient {c.patient_display}</span>
                {c.state && <span className="flex items-center gap-1.5 text-[13px] capitalize"><span className={`size-2 rounded-full ${DOT[c.state] ?? "bg-muted-foreground"}`} />{c.state}</span>}
                <span className="text-[13px] text-muted-foreground">{movedAgo(c.last_movement_at)}</span>
                {c.open_requests > 0 && <span className="rounded-full bg-primary/15 px-2 py-0.5 text-xs text-primary">{c.open_requests} request{c.open_requests > 1 ? "s" : ""} for you</span>}
                <ChevronRight className="ml-auto size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
