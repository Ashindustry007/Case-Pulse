"use client";
import { AlertTriangle, User } from "lucide-react";
import { Cited } from "@/components/citations/Cited";
import { Chips } from "@/components/citations/CitationChip";
import { apiUrl } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { isNotFound, type Overview } from "@/lib/types";
import { CostPill } from "./CostPill";

export function MatterHeader({ overview: o }: { overview: Overview }) {
  const lcc = isNotFound(o.last_client_contact) ? null : o.last_client_contact;
  return (
    <section className="space-y-2">
      <CostPill matterId={o.matter.id} lastSyncedAt={o.last_synced_at} />
      <div className="flex items-start gap-4">
        {o.client.photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={apiUrl(o.client.photo_url)} alt="Client" className="h-16 w-16 rounded object-cover" />
        ) : <div className="grid h-16 w-16 place-items-center rounded bg-muted"><User className="h-8 w-8 text-muted-foreground" /></div>}
        <div className="space-y-1">
          <h1 className="text-lg font-semibold">
            {o.client.name}{o.client.age != null && <span className="font-normal text-muted-foreground"> · {o.client.age}y</span>}
            {o.client.photo_citation && <Chips citations={[o.client.photo_citation]} />}
          </h1>
          <p className="text-sm">
            DOI <Cited value={o.date_of_incident} render={(v: string) => fmtDate(v)} /> · SOL <Cited value={o.statute_of_limitations} render={(v: string) => fmtDate(v)} />
          </p>
          <p className="text-sm">
            Last client contact:{" "}
            {lcc ? (
              <span className={lcc.value.days_ago > 30 ? "font-medium text-amber-700 dark:text-amber-400" : ""}>
                {lcc.value.days_ago}d ago · {lcc.value.channel}{lcc.value.by && ` · ${lcc.value.by}`}
                <Chips citations={lcc.citations} />
                {lcc.value.days_ago > 30 && <AlertTriangle className="ml-1 inline h-4 w-4" />}
              </span>
            ) : <Cited value={o.last_client_contact} />}
          </p>
        </div>
        <StageBar stages={o.stage.stages ?? []} index={o.stage.index ?? null} current={o.stage.current ?? null} />
      </div>
    </section>
  );
}

function StageBar({ stages, index, current }: { stages: string[]; index: number | null; current: string | null }) {
  if (!stages.length) return current ? <span className="ml-auto text-sm">Stage: {current}</span> : null;
  return (
    <ol className="ml-auto flex gap-1 text-[11px]">
      {stages.map((s, i) => (
        <li key={s} className={`rounded px-2 py-1 ${index != null && i <= index ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{s}</li>
      ))}
    </ol>
  );
}
