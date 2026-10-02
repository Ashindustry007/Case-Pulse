"use client";
import { ChevronRight, Link2 } from "lucide-react";
import Link from "next/link";
import { ErrorNote, Loading } from "@/components/common/states";
import { buttonVariants } from "@/components/ui/button";
import { API_URL } from "@/lib/api";
import { daysAgo, fmtDate } from "@/lib/format";
import type { MatterSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type SyncStatus = { connected: boolean; clio_user?: string | null; last_synced_at?: string | null };

function ago(iso?: string | null) {
  if (!iso) return "";
  const d = daysAgo(iso);
  return d <= 0 ? "today" : d === 1 ? "yesterday" : d < 60 ? `${d}d ago` : fmtDate(iso);
}

export default function MattersPage() {
  const matters = useApi<MatterSummary[]>("/api/matters");
  const sync = useApi<SyncStatus>("/api/sync/status");
  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Matters</h1>
          <p className="mt-1 flex items-center gap-2 text-[13px] text-muted-foreground">
            <span className={`size-1.5 rounded-full ${sync.data?.connected ? "bg-success" : "bg-muted-foreground/50"}`} />
            {sync.data?.connected ? `Clio connected${sync.data.clio_user ? ` as ${sync.data.clio_user}` : ""} · last sync ${fmtDate(sync.data.last_synced_at)}` : "Clio not connected"}
          </p>
        </div>
        {!sync.data?.connected && <a href={`${API_URL}/auth/clio/login`} className={buttonVariants({ size: "sm", className: "ml-auto" })}><Link2 /> Connect Clio</a>}
      </div>
      <ErrorNote error={matters.error} />
      {matters.loading ? <Loading lines={4} /> : (
        <ul className="space-y-3">
          {matters.data?.map((m) => (
            <li key={m.id}>
              <Link href={`/matters/${m.id}`} className="group flex items-center gap-4 rounded-xl border bg-card px-5 py-4 transition-colors hover:border-primary/50 hover:bg-accent/30">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[15px] font-medium">{m.client_name ?? m.description}</p>
                  <p className="truncate text-[13px] text-muted-foreground">{m.display_number} · {m.description}</p>
                </div>
                {m.stage && <span className="rounded-full border border-primary/40 px-2.5 py-0.5 text-xs text-primary">{m.stage}</span>}
                <span className="hidden w-24 text-right text-xs text-muted-foreground sm:block">{m.last_activity_at ? `active ${ago(m.last_activity_at)}` : ""}</span>
                <ChevronRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
