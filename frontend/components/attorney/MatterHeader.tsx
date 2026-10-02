"use client";
import { User } from "lucide-react";
import { Cited } from "@/components/citations/Cited";
import { Chips } from "@/components/citations/CitationChip";
import { StageStepper } from "@/components/common/StageStepper";
import { apiUrl } from "@/lib/api";
import { daysAgo, fmtDate } from "@/lib/format";
import { isNotFound, type Overview } from "@/lib/types";
import { CostPill } from "./CostPill";

// Mirrors the backend rule: once suit is filed (or later), a past statute-of-limitations date was met, not missed.
const SUIT_FILED = /litigation|suit|trial|settle|disburse|closed|appeal/i;

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 bg-card px-4 py-3">
      <dt className="section-label">{label}</dt>
      <dd className="mt-1 text-[15px] font-medium">{children}</dd>
    </div>
  );
}

export function MatterHeader({ overview: o }: { overview: Overview }) {
  const lcc = isNotFound(o.last_client_contact) ? null : o.last_client_contact;
  const stale = lcc ? lcc.value.days_ago > 30 : false;
  const sol = isNotFound(o.statute_of_limitations) ? null : o.statute_of_limitations;
  const solDays = sol ? -daysAgo(sol.value) : null;
  const suitFiled = SUIT_FILED.test(o.stage.current ?? "");
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-4">
        {o.client.photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={apiUrl(o.client.photo_url)} alt="Client" className="size-14 rounded-full object-cover ring-2 ring-border" />
        ) : <div className="grid size-14 place-items-center rounded-full bg-muted ring-2 ring-border"><User className="size-6 text-muted-foreground" /></div>}
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">
            {o.client.name}
            {o.client.age != null && <span className="ml-2 text-base font-normal text-muted-foreground">{o.client.age}y</span>}
            {o.client.photo_citation && <Chips citations={[o.client.photo_citation]} />}
          </h1>
          <p className="truncate text-[13px] text-muted-foreground">{[o.matter.display_number, o.matter.description].filter(Boolean).join(" · ")}</p>
        </div>
        <div className="ml-auto"><StageStepper stages={o.stage.stages ?? []} index={o.stage.index ?? null} current={o.stage.current ?? null} /></div>
      </div>

      <dl className="grid grid-cols-1 gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-3">
        <Fact label="Date of incident"><Cited value={o.date_of_incident} render={(v: string) => fmtDate(v)} /></Fact>
        <Fact label="Statute of limitations">
          <Cited value={o.statute_of_limitations} render={(v: string) => fmtDate(v)} />
          {solDays != null && (
            <span className={`ml-2 text-xs font-normal ${solDays < 0 ? (suitFiled ? "text-success" : "text-danger") : solDays < 90 ? "text-warning" : "text-muted-foreground"}`}>
              {solDays < 0 ? (suitFiled ? "met — suit filed" : `passed ${-solDays}d ago`) : `${solDays}d left`}
            </span>
          )}
        </Fact>
        <Fact label="Last client contact">
          {lcc ? (
            <span>
              <span className={stale ? "text-warning" : ""}>{lcc.value.days_ago}d ago</span>
              <span className="text-[13px] font-normal text-muted-foreground"> · {lcc.value.channel}{lcc.value.by && ` · ${lcc.value.by}`}</span>
              <Chips citations={lcc.citations} />
            </span>
          ) : <Cited value={o.last_client_contact} />}
        </Fact>
      </dl>
      <CostPill matterId={o.matter.id} lastSyncedAt={o.last_synced_at} />
    </section>
  );
}
