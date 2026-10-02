"use client";
import { ArrowRight, Hourglass, Phone, Scale, ShieldCheck, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { Chips } from "@/components/citations/CitationChip";
import { Cited } from "@/components/citations/Cited";
import { Skeleton } from "@/components/ui/skeleton";
import { daysAgo, fmtDate, fmtMoneyShort } from "@/lib/format";
import { isNotFound, type Brief, type Overview } from "@/lib/types";
import { short } from "./CoverageTile";

type Tone = "gold" | "success" | "warning" | "danger" | "muted";
const TONE: Record<Tone, string> = {
  gold: "bg-primary/12 text-primary", success: "bg-success/12 text-success", warning: "bg-warning/12 text-warning",
  danger: "bg-danger/12 text-danger", muted: "bg-muted text-muted-foreground",
};
const VALUE_TONE: Record<Tone, string> = { gold: "text-primary", success: "text-success", warning: "text-warning", danger: "text-danger", muted: "" };

// Mirrors the backend rule: once suit is filed (or later), a past statute-of-limitations date was met, not missed.
const SUIT_FILED = /litigation|suit|trial|settle|disburse|closed|appeal/i;

function Tile({ icon: Icon, tone, label, value, sub, href }: {
  icon: LucideIcon; tone: Tone; label: string; value: React.ReactNode; sub?: React.ReactNode; href?: string;
}) {
  return (
    <div className="group relative flex min-w-0 gap-3 rounded-xl border bg-card p-4">
      <span className={`grid size-10 shrink-0 place-items-center rounded-lg ${TONE[tone]}`}><Icon className="size-5" aria-hidden /></span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className={`truncate text-[22px] font-semibold leading-tight tracking-tight ${VALUE_TONE[tone]}`}>{value}</div>
        {sub && <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>}
      </div>
      {href && (
        <Link href={href} aria-label={`${label} details`} className="absolute right-3 top-3 text-muted-foreground opacity-60 transition-opacity hover:text-primary group-hover:opacity-100">
          <ArrowRight className="size-4" />
        </Link>
      )}
    </div>
  );
}

/** Four numbers an attorney checks first. Each links to the page with the full, cited breakdown. */
export function OverviewKpis({ overview: o, brief: b, matterId }: { overview?: Overview; brief?: Brief; matterId: number }) {
  if (!o || !b) return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-[84px] rounded-xl" />)}</div>;
  const money = `/matters/${matterId}/money`;

  const worth = isNotFound(b.worth) ? null : b.worth;

  const cov = b.coverage;
  const person = isNotFound(cov.bi_per_person) ? null : cov.bi_per_person.value;
  const accident = isNotFound(cov.bi_per_accident) ? null : cov.bi_per_accident.value;

  const sol = isNotFound(o.statute_of_limitations) ? null : o.statute_of_limitations;
  const solDays = sol ? -daysAgo(sol.value) : null;
  const suitFiled = SUIT_FILED.test(o.stage.current ?? "");
  const solTone: Tone = solDays == null ? "muted" : solDays < 0 ? (suitFiled ? "success" : "danger") : solDays < 90 ? "warning" : "gold";

  const lcc = isNotFound(o.last_client_contact) ? null : o.last_client_contact;
  const lccTone: Tone = !lcc ? "muted" : lcc.value.days_ago > 30 ? "warning" : "success";

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Tile icon={Scale} tone="gold" label="Estimated case value" href={money}
        value={worth ? `${fmtMoneyShort(worth.low)} – ${fmtMoneyShort(worth.high)}` : <span className="text-base text-muted-foreground">not found in file</span>}
        sub={worth ? `Estimate · ${worth.assumptions.length} cited assumptions` : undefined} />
      <Tile icon={ShieldCheck} tone={cov.confirmed ? "success" : person || accident ? "gold" : "muted"} label="Insurance coverage" href={money}
        value={person || accident ? `${person ? short(person) : "—"} / ${accident ? short(accident) : "—"}` : <span className="text-base text-muted-foreground">no limits found</span>}
        sub={<span className="flex items-center gap-1 truncate"><Cited value={cov.carrier} />{cov.confirmed && <span className="text-success">· confirmed</span>}</span>} />
      <Tile icon={Hourglass} tone={solTone} label="Statute of limitations"
        value={solDays == null ? <span className="text-base text-muted-foreground">not found in file</span> : solDays < 0 ? (suitFiled ? "Met" : "Passed") : `${solDays} days`}
        sub={sol && <span>{fmtDate(sol.value)}{solDays != null && solDays < 0 && suitFiled && " · suit filed"}<Chips citations={sol.citations} /></span>} />
      <Tile icon={Phone} tone={lccTone} label="Last client contact"
        value={lcc ? `${lcc.value.days_ago}d ago` : <span className="text-base text-muted-foreground">not found in file</span>}
        sub={lcc && <span className="capitalize">{lcc.value.channel}{lcc.value.by && ` · ${lcc.value.by}`}<Chips citations={lcc.citations} /></span>} />
    </div>
  );
}
