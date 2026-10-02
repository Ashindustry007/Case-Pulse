"use client";
import { CalendarDays, User } from "lucide-react";
import { Cited } from "@/components/citations/Cited";
import { Chips } from "@/components/citations/CitationChip";
import { StageStepper } from "@/components/common/StageStepper";
import { apiUrl } from "@/lib/api";
import { daysAgo, fmtDate } from "@/lib/format";
import { isNotFound, type Overview } from "@/lib/types";

/** "~1 year, 6 months ago" from a past date. */
export function sinceText(iso: string): string {
  const d = daysAgo(iso);
  if (d < 0) return `in ${-d}d`;
  if (d < 45) return `${d} days ago`;
  const months = Math.round(d / 30.44);
  const y = Math.floor(months / 12), m = months % 12;
  return `~${[y && `${y} year${y > 1 ? "s" : ""}`, m && `${m} month${m > 1 ? "s" : ""}`].filter(Boolean).join(", ")} ago`;
}

/** Hero: who, which matter, when it happened, where it stands. Numbers live in the KPI row below. */
export function MatterHeader({ overview: o }: { overview: Overview }) {
  const doi = isNotFound(o.date_of_incident) ? null : o.date_of_incident.value;
  return (
    <section className="flex flex-wrap items-center gap-x-6 gap-y-4">
      <div className="flex min-w-0 items-center gap-4">
        {o.client.photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={apiUrl(o.client.photo_url)} alt="Client" className="size-16 rounded-full object-cover ring-2 ring-border" />
        ) : <div className="grid size-16 place-items-center rounded-full bg-muted ring-2 ring-border"><User className="size-6 text-muted-foreground" /></div>}
        <div className="min-w-0">
          <h1 className="text-[26px] font-semibold leading-tight tracking-tight">
            {o.client.name}
            {o.client.age != null && <span className="ml-2 text-base font-normal text-muted-foreground">{o.client.age}y</span>}
            {o.client.photo_citation && <Chips citations={[o.client.photo_citation]} />}
          </h1>
          <p className="truncate text-[13.5px] text-muted-foreground">
            {[o.matter.display_number && `Matter ${o.matter.display_number}`, o.matter.description].filter(Boolean).join("  ·  ")}
          </p>
          <p className="mt-1 flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-[13px] text-muted-foreground">
            <CalendarDays className="size-3.5" aria-hidden /> Incident{" "}
            <span className="text-foreground"><Cited value={o.date_of_incident} render={(v: string) => fmtDate(v)} /></span>
            {doi && <span>· {sinceText(doi)}</span>}
          </p>
        </div>
      </div>
      <div className="w-full rounded-xl border bg-card px-4 pb-3 pt-3.5">
        <div className="mb-3 flex items-baseline gap-2">
          <p className="section-label">Case stage</p>
          {o.stage.index != null && <span className="text-xs text-muted-foreground">{o.stage.current} · {o.stage.index + 1} of {o.stage.stages?.length}</span>}
        </div>
        <div className="overflow-x-auto"><div className="min-w-[560px]">
          <StageStepper stages={o.stage.stages ?? []} index={o.stage.index ?? null} current={o.stage.current ?? null} />
        </div></div>
      </div>
    </section>
  );
}
