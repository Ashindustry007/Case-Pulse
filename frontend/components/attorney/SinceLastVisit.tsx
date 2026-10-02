"use client";
import { CircleCheck, History } from "lucide-react";
import { useEffect, useState } from "react";
import { Chips } from "@/components/citations/CitationChip";
import { Importance } from "@/components/common/ImportanceDot";
import { RichText } from "@/components/common/RichText";
import { Panel, Section } from "@/components/common/Section";
import { ErrorNote, Loading } from "@/components/common/states";
import { api } from "@/lib/api";
import { fmtDate, fmtDateTime } from "@/lib/format";
import { plain } from "@/lib/richtext";
import type { Changes, Delta, VisitResponse } from "@/lib/types";

const SHOWN = 5;

/** F1. POST /visits → baseline → /changes + /delta. Badges are computed per request, never cached client-side. */
export function SinceLastVisit({ matterId }: { matterId: number }) {
  const [s, set] = useState<{ visit?: VisitResponse; changes?: Changes; delta?: Delta; error?: Error }>({});
  const [all, setAll] = useState(false);
  const [fullSummary, setFullSummary] = useState(false);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        // React dev StrictMode runs this twice; the backend reuses visits within 30 min, so the baseline is stable.
        const visit = await api<VisitResponse>(`/api/matters/${matterId}/visits`, { method: "POST" });
        const q = visit.previous_visit_at ? `?since=${encodeURIComponent(visit.previous_visit_at)}` : "";
        const [changes, delta] = await Promise.all([
          api<Changes>(`/api/matters/${matterId}/changes${q}`),
          api<Delta>(`/api/matters/${matterId}/delta${q}`).catch(() => undefined),
        ]);
        if (!cancelled) set({ visit, changes, delta });
      } catch (error) {
        if (!cancelled) set({ error: error as Error });
      }
    })();
    return () => { cancelled = true; };
  }, [matterId]);

  const { visit, changes, delta } = s;
  const first = changes?.first_visit || visit?.first_visit;
  const title = first
    ? "First time opening this matter — showing the last 14 days"
    : `Since your last visit · ${fmtDateTime(changes?.since ?? visit?.previous_visit_at)}`;
  const items = changes?.items ?? [];
  const visible = all ? items : items.slice(0, SHOWN);
  const summary = delta?.summary ?? [];

  return (
    <Section icon={History} title={title} action={changes && <span className="text-muted-foreground">{items.length} change{items.length === 1 ? "" : "s"} · ranked by importance</span>}>
      <Panel className="space-y-4">
        <ErrorNote error={s.error} />
        {!changes && !s.error && <Loading lines={4} />}

        {summary.length > 0 && (
          <div className="rounded-lg bg-accent/40 p-3.5">
            <ul className="space-y-2 text-[14px] leading-relaxed">
              {summary.map((sen, i) => (
                <li key={i} className={`flex gap-2 ${fullSummary ? "" : "line-clamp-3"}`}>
                  <span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary/70" aria-hidden />
                  <span><RichText text={sen.text} /><Chips citations={sen.citations} /></span>
                </li>
              ))}
            </ul>
            {summary.some((x) => plain(x.text).length > 180) && (
              <button type="button" className="mt-2 text-xs text-primary hover:underline" onClick={() => setFullSummary((v) => !v)}>
                {fullSummary ? "Show less" : "Show full summary"}
              </button>
            )}
          </div>
        )}

        {changes && items.length === 0 && (
          <p className="flex items-start gap-2 text-[14px] text-muted-foreground">
            <CircleCheck className="mt-0.5 size-4 shrink-0 text-success" />
            <span>
              {changes.empty_message ?? `Nothing has changed since your last visit (${fmtDateTime(changes.since)}).`}
              {changes.last_activity && <> Last activity on the case: {fmtDate(changes.last_activity.at)}, {changes.last_activity.description}<Chips citations={changes.last_activity.citations} /></>}
            </span>
          </p>
        )}

        {items.length > 0 && (
          <ul className="divide-y">
            {visible.map((c) => (
              <li key={`${c.record_id}-${c.change}`} className="grid grid-cols-[auto_1fr] gap-3 py-2.5 first:pt-0 last:pb-0">
                <Importance n={c.importance} />
                <div className="min-w-0">
                  <p className="text-[14px] leading-snug">
                    <span className="font-medium"><RichText text={c.title} /></span>
                    {c.change !== "changed" && <span className="ml-2 rounded-full border px-1.5 py-px text-[10px] uppercase tracking-wider text-muted-foreground">{c.change}</span>}
                    <Chips citations={c.citations} />
                  </p>
                  {c.why_it_matters && <p className="mt-0.5 text-[13px] text-muted-foreground">{c.why_it_matters}</p>}
                </div>
              </li>
            ))}
          </ul>
        )}
        {items.length > SHOWN && (
          <button type="button" className="text-xs text-primary hover:underline" onClick={() => setAll((v) => !v)}>
            {all ? "Show fewer" : `Show ${items.length - SHOWN} more`}
          </button>
        )}
      </Panel>
    </Section>
  );
}
