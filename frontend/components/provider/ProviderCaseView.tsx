/** Provider case page body. PURE (props in, no fetching) so the Share Composer preview renders the exact same thing.
 *  Renders only keys that exist; never shows "redacted". Must not import attorney components (ESLint enforces). */
import { Activity, Check, ClipboardList, FileText, HeartPulse, Receipt, Shield, Tag, TrendingUp, Users } from "lucide-react";
import { Panel, Section } from "@/components/common/Section";
import { Button } from "@/components/ui/button";
import { daysAgo, fmtDate, fmtMoney } from "@/lib/format";
import type { ProviderCase } from "@/lib/types";

const DOT: Record<string, string> = { active: "bg-success", quiet: "bg-warning", dormant: "bg-muted-foreground", closed: "bg-muted-foreground/60" };

type Props = {
  c: ProviderCase;
  onMarkSent?: (requestId: string) => void;
  docHref?: (documentId: string) => string;
  preview?: boolean;
};

export function ProviderCaseView({ c, onMarkSent, docHref, preview }: Props) {
  const hb = c.heartbeat;
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Patient {c.patient_display}</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">Shared by {c.shared_by ? `${c.shared_by} · ${c.firm_name}` : c.firm_name}{!preview && ` · version ${c.policy_version}`}</p>
      </header>

      {hb && (
        <Panel className="space-y-3">
          <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[15px]">
            <span className="flex items-center gap-2 font-semibold capitalize"><span className={`size-2.5 rounded-full ${DOT[hb.state]}`} />{hb.state}</span>
            {hb.last_movement && <span className="text-muted-foreground">Last movement {fmtDate(hb.last_movement.date)}: <span className="text-foreground">“{hb.last_movement.text}”</span></span>}
          </p>
          {hb.stage?.stages?.length ? (
            <ol className="flex flex-wrap gap-1.5 text-[11px]">
              {hb.stage.stages.map((s, i) => (
                <li key={s} className={`rounded-full px-2.5 py-0.5 ${hb.stage?.index != null && i === hb.stage.index ? "bg-primary text-primary-foreground" : hb.stage?.index != null && i < hb.stage.index ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"}`}>{s}</li>
              ))}
            </ol>
          ) : null}
        </Panel>
      )}

      {c.status_note && <Panel className="text-[14px] leading-relaxed">{c.status_note}</Panel>}

      {c.requests && (
        <Section icon={ClipboardList} title="What the firm needs from you">
          {c.requests.length === 0 ? <Panel className="text-muted-foreground">Nothing outstanding.</Panel> : (
            <ul className="space-y-2.5">
              {c.requests.map((r) => (
                <li key={r.id} className={`rounded-xl border bg-card p-4 ${r.state === "completed" ? "opacity-70" : ""}`}>
                  <div className="flex flex-wrap items-start gap-3">
                    <span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border ${r.state === "completed" ? "border-success bg-success/15 text-success" : ""}`}>{r.state === "completed" && <Check className="size-3.5" />}</span>
                    <div className="min-w-0 flex-1">
                      <p className={`text-[14px] font-medium leading-snug ${r.state === "completed" ? "line-through" : ""}`}>{r.description}</p>
                      <p className="mt-0.5 text-xs text-muted-foreground">{r.requested_at && `Requested ${fmtDate(r.requested_at)}`}{r.channel && ` by ${r.channel}`}</p>
                      {r.citations?.[0] && <blockquote className="mt-2 border-l-2 border-primary/50 pl-3 text-[13px] italic text-muted-foreground">“{r.citations[0].excerpt}”</blockquote>}
                    </div>
                    {r.state === "open" && <Button size="sm" variant="outline" disabled={!onMarkSent} onClick={() => onMarkSent?.(r.id)}>Mark sent</Button>}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}

      {c.case_details?.length ? (
        <Section icon={Tag} title="Case details">
          <Panel>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-[14px] sm:grid-cols-[minmax(130px,auto)_1fr]">
              {c.case_details.map((d) => (
                <div key={d.label} className="contents">
                  <dt className="text-muted-foreground">{d.label}</dt>
                  <dd className="whitespace-pre-line">{d.value}</dd>
                </div>
              ))}
            </dl>
          </Panel>
        </Section>
      ) : null}

      {(c.coverage || c.case_value || c.bills) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {c.coverage && (
            <Section icon={Shield} title="Coverage">
              <Panel className="space-y-1 text-[14px]">
                <p className="font-medium">{c.coverage.confirmed ? "Coverage confirmed" : "Coverage not yet confirmed"}</p>
                {c.coverage.carrier && <p className="text-muted-foreground">{c.coverage.carrier}</p>}
                {c.coverage.limits_text && <p className="text-muted-foreground">{c.coverage.limits_text}</p>}
              </Panel>
            </Section>
          )}
          {c.case_value && (
            <Section icon={TrendingUp} title="Case value (estimate)">
              <Panel className="text-xl font-semibold text-primary">{fmtMoney(c.case_value.low)} – {fmtMoney(c.case_value.high)}</Panel>
            </Section>
          )}
          {c.bills && (
            <Section icon={Receipt} title="Your bills">
              <Panel className="space-y-1 text-[14px]">
                <p className="text-xl font-semibold">{fmtMoney(c.bills.billed)} <span className="text-[13px] font-normal text-muted-foreground">billed</span></p>
                <p className="text-muted-foreground">{c.bills.balance != null && `${fmtMoney(c.bills.balance)} balance`}{c.bills.lien && `${c.bills.balance != null ? " · " : ""}lien on file`}</p>
              </Panel>
            </Section>
          )}
        </div>
      )}

      {c.documents && (
        <Section icon={FileText} title="Documents shared with you">
          {c.documents.length === 0 ? <Panel className="text-muted-foreground">No documents shared.</Panel> : (
            <Panel className="p-0">
              <ul className="divide-y">
                {c.documents.map((d) => (
                  <li key={d.id} className="flex items-center gap-3 px-4 py-3 text-[14px]">
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                    <span className="min-w-0 flex-1 truncate">{d.title}{d.page_count && <span className="ml-2 text-xs text-muted-foreground">{d.page_count} pp</span>}</span>
                    {d.shared_at && <span className="hidden text-xs text-muted-foreground sm:inline">shared {fmtDate(d.shared_at)}</span>}
                    {docHref ? <a className="text-sm text-primary hover:underline" href={docHref(d.id)} target="_blank" rel="noreferrer">Open</a> : <span className="text-xs text-muted-foreground">Open</span>}
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </Section>
      )}

      {hb?.recent_movement?.length ? (
        <Section icon={HeartPulse} title="Recent movement">
          <Panel>
            <ol className="space-y-2.5 border-l pl-4 text-[14px]">
              {hb.recent_movement.map((m, i) => (
                <li key={i} className="relative before:absolute before:-left-[21px] before:top-2 before:size-1.5 before:rounded-full before:bg-primary/70">
                  <span className="text-xs text-muted-foreground">{fmtDate(m.date)}</span><br />{m.text}
                </li>
              ))}
            </ol>
          </Panel>
        </Section>
      ) : null}

      {c.adherence && (
        <Section icon={Activity} title="Treatment adherence">
          <Panel className="space-y-1 text-[14px]">
            <p>{c.adherence.visits.length} visits · last {fmtDate(c.adherence.visits.at(-1))}{c.adherence.current_gap_days != null && ` · ${c.adherence.current_gap_days}d since last visit`}</p>
            {c.adherence.gaps?.length ? <p className="text-warning">Gaps: {c.adherence.gaps.map((g) => `${g.days}d (${fmtDate(String(g.from))}–${fmtDate(String(g.to))})`).join(", ")}</p> : null}
          </Panel>
        </Section>
      )}

      {c.other_care && (
        <Section icon={Users} title="Other providers' care">
          <Panel><ul className="space-y-1 text-[14px]">{c.other_care.map((o) => <li key={o.provider_name}>{o.provider_name} <span className="text-muted-foreground">· {fmtDate(o.first_visit)}–{fmtDate(o.last_visit)}</span></li>)}</ul></Panel>
        </Section>
      )}
    </div>
  );
}

export function movedAgo(iso?: string | null) {
  return iso ? `moved ${daysAgo(iso)}d ago` : "";
}
