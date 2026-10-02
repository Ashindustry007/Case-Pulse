"use client";
import Link from "next/link";
import { ErrorNote, Loading } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { API_URL } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import type { MatterSummary } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type SyncStatus = { connected: boolean; clio_user?: string | null; last_synced_at?: string | null };

export default function MattersPage() {
  const matters = useApi<MatterSummary[]>("/api/matters");
  const sync = useApi<SyncStatus>("/api/sync/status");
  return (
    <div className="mx-auto max-w-5xl space-y-4 p-6">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-semibold">Matters</h1>
        <span className="text-xs text-muted-foreground">
          {sync.data?.connected ? `Clio connected${sync.data.clio_user ? ` as ${sync.data.clio_user}` : ""} · last sync ${fmtDate(sync.data.last_synced_at)}` : "Clio not connected"}
        </span>
        {!sync.data?.connected && <a href={`${API_URL}/auth/clio/login`} className={buttonVariants({ size: "sm", className: "ml-auto" })}>Connect Clio</a>}
      </div>
      <ErrorNote error={matters.error} />
      {matters.loading ? <Loading /> : (
        <ul className="divide-y rounded border">
          {matters.data?.map((m) => (
            <li key={m.id}>
              <Link href={`/matters/${m.id}`} className="flex items-center gap-3 p-3 hover:bg-muted/50">
                <span className="font-medium">{m.client_name ?? m.description}</span>
                <span className="text-sm text-muted-foreground">{m.display_number} · {m.description}</span>
                {m.stage && <Badge variant="secondary" className="ml-auto">{m.stage}</Badge>}
                <span className="text-xs text-muted-foreground">{fmtDate(m.last_activity_at)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
