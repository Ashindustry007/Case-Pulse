/** Provider case page body. PURE (props in, no fetching) so the Share Composer preview renders the exact same thing.
 *  Renders only keys that exist; never shows "redacted". Must not import attorney components (ESLint enforces). */
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { daysAgo, fmtDate, fmtMoney } from "@/lib/format";
import type { ProviderCase } from "@/lib/types";

const DOT: Record<string, string> = { active: "bg-emerald-500", quiet: "bg-amber-500", dormant: "bg-slate-400", closed: "bg-slate-600" };

type Props = {
  c: ProviderCase;
  onMarkSent?: (requestId: string) => void;
  docHref?: (documentId: string) => string;
  preview?: boolean;
};

export function ProviderCaseView({ c, onMarkSent, docHref, preview }: Props) {
  const hb = c.heartbeat;
  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-lg font-semibold">Patient {c.patient_display}</h1>
        <p className="text-xs text-muted-foreground">shared by {c.shared_by ?? c.firm_name} · {c.firm_name}{!preview && ` · policy v${c.policy_version}`}</p>
      </div>
      {hb && (
        <Card><CardContent className="space-y-2 pt-4 text-sm">
          <p className="flex items-center gap-2 font-medium">
            <span className={`h-2.5 w-2.5 rounded-full ${DOT[hb.state]}`} /> {hb.state.toUpperCase()}
            {hb.last_movement && <span className="font-normal">· Last movement {fmtDate(hb.last_movement.date)}: “{hb.last_movement.text}”</span>}
          </p>
          {hb.stage?.stages?.length ? (
            <ol className="flex flex-wrap gap-1 text-[11px]">
              {hb.stage.stages.map((s, i) => <li key={s} className={`rounded px-2 py-0.5 ${hb.stage?.index != null && i <= hb.stage.index ? "bg-primary text-primary-foreground" : "bg-muted"}`}>{s}</li>)}
            </ol>
          ) : null}
        </CardContent></Card>
      )}
      {c.status_note && <Card><CardContent className="pt-4 text-sm">{c.status_note}</CardContent></Card>}
      {c.case_details?.length ? (
        <Section title="Case details">
          <dl className="grid grid-cols-[minmax(120px,auto)_1fr] gap-x-4 gap-y-1">
            {c.case_details.map((d) => (
              <div key={d.label} className="contents">
                <dt className="text-muted-foreground">{d.label}</dt>
                <dd className="whitespace-pre-line">{d.value}</dd>
              </div>
            ))}
          </dl>
        </Section>
      ) : null}
      {c.coverage && (
        <Section title="Coverage">
          {c.coverage.confirmed ? "✔ Coverage confirmed" : "Coverage not yet confirmed"}
          {c.coverage.carrier && <> · {c.coverage.carrier}</>}
          {c.coverage.limits_text && <p className="text-muted-foreground">{c.coverage.limits_text}</p>}
        </Section>
      )}
      {c.case_value && <Section title="Case value (estimate)">{fmtMoney(c.case_value.low)} – {fmtMoney(c.case_value.high)}</Section>}
      {c.requests && (
        <Section title="What the firm needs from you">
          {c.requests.length === 0 ? <p className="text-muted-foreground">Nothing outstanding.</p> : (
            <ul className="space-y-2">
              {c.requests.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center gap-2">
                  <span>{r.state === "completed" ? "☑" : "☐"} {r.description}</span>
                  <span className="text-xs text-muted-foreground">{r.requested_at && `requested ${fmtDate(r.requested_at)}`}{r.channel && ` by ${r.channel}`}</span>
                  {r.citations?.[0] && <blockquote className="w-full border-l-2 pl-2 text-xs italic">“{r.citations[0].excerpt}”</blockquote>}
                  {r.state === "open" && (
                    <Button size="sm" variant="outline" className="ml-auto" disabled={!onMarkSent} onClick={() => onMarkSent?.(r.id)}>Mark sent</Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}
      {c.bills && (
        <Section title="Your bills">
          {fmtMoney(c.bills.billed)} billed{c.bills.balance != null && ` · ${fmtMoney(c.bills.balance)} balance`}{c.bills.lien && " · lien on file"}
        </Section>
      )}
      {c.documents && (
        <Section title="Recently shared documents">
          {c.documents.length === 0 ? <p className="text-muted-foreground">No documents shared.</p> : (
            <ul className="space-y-1">
              {c.documents.map((d) => (
                <li key={d.id} className="flex items-center gap-2">
                  {d.title}{d.page_count && <span className="text-xs text-muted-foreground">({d.page_count} pp)</span>}
                  {d.shared_at && <span className="text-xs text-muted-foreground">· shared {fmtDate(d.shared_at)}</span>}
                  {docHref ? <a className="ml-auto text-sm underline" href={docHref(d.id)} target="_blank" rel="noreferrer">Open</a> : <span className="ml-auto text-xs text-muted-foreground">Open</span>}
                </li>
              ))}
            </ul>
          )}
        </Section>
      )}
      {hb?.recent_movement?.length ? (
        <Section title="Recent movement">{hb.recent_movement.map((m) => `${fmtDate(m.date)} ${m.text}`).join(" · ")}</Section>
      ) : null}
      {c.adherence && (
        <Section title="Treatment adherence">
          {c.adherence.visits.length} visits · last {fmtDate(c.adherence.visits.at(-1))}
          {c.adherence.current_gap_days != null && ` · ${c.adherence.current_gap_days}d since last visit`}
          {c.adherence.gaps?.length ? <p className="text-amber-700">Gaps: {c.adherence.gaps.map((g) => `${g.days}d (${fmtDate(String(g.from))}–${fmtDate(String(g.to))})`).join(", ")}</p> : null}
        </Section>
      )}
      {c.other_care && (
        <Section title="Other providers' care">
          <ul>{c.other_care.map((o) => <li key={o.provider_name}>{o.provider_name} · {fmtDate(o.first_visit)}–{fmtDate(o.last_visit)}</li>)}</ul>
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">{title}</CardTitle></CardHeader>
      <CardContent className="text-sm">{children}</CardContent>
    </Card>
  );
}

export function movedAgo(iso?: string | null) {
  return iso ? `moved ${daysAgo(iso)}d ago` : "";
}
