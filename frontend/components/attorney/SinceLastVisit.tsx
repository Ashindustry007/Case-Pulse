"use client";
import { useEffect, useState } from "react";
import { Chips } from "@/components/citations/CitationChip";
import { ErrorNote, Loading } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { fmtDate, fmtDateTime } from "@/lib/format";
import type { Changes, Delta, VisitResponse } from "@/lib/types";

/** F1. POST /visits → baseline → /changes + /delta. Badges are computed per request, never cached client-side. */
export function SinceLastVisit({ matterId }: { matterId: number }) {
  const [s, set] = useState<{ visit?: VisitResponse; changes?: Changes; delta?: Delta; error?: Error }>({});
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
  const title = changes?.first_visit || visit?.first_visit
    ? "🆕 First time opening this matter, showing the last 14 days"
    : `🆕 Since your last visit (${fmtDateTime(changes?.since ?? visit?.previous_visit_at)})${changes ? ` · ${changes.items.length} changes, by importance` : ""}`;

  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle className="text-sm">{title}</CardTitle></CardHeader>
      <CardContent className="space-y-2 text-sm">
        <ErrorNote error={s.error} />
        {!changes && !s.error && <Loading />}
        {delta && delta.summary.length > 0 && (
          <p className="rounded bg-muted/50 p-2">{delta.summary.map((sen, i) => <span key={i}>{sen.text}<Chips citations={sen.citations} /> </span>)}</p>
        )}
        {changes && changes.items.length === 0 && (
          <p className="text-muted-foreground">
            {changes.empty_message ?? `Nothing has changed since your last visit (${fmtDateTime(changes.since)}).`}
            {changes.last_activity && <> Last activity on the case: {fmtDate(changes.last_activity.at)}, {changes.last_activity.description}<Chips citations={changes.last_activity.citations} /></>}
          </p>
        )}
        <ul className="space-y-1">
          {changes?.items.map((c) => (
            <li key={`${c.record_id}-${c.change}`} className="flex gap-2">
              <span className="w-5 text-right font-mono font-semibold">{c.importance ?? "–"}</span>
              <div>
                <span className="font-medium">{c.title}</span>
                {c.change !== "changed" && <Badge variant="outline" className="ml-1 text-[10px]">{c.change}</Badge>}
                <Chips citations={c.citations} />
                {c.why_it_matters && <span className="text-muted-foreground"> · why: {c.why_it_matters}</span>}
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
