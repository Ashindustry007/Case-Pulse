"use client";
import { useState } from "react";
import { Chips } from "@/components/citations/CitationChip";
import { Loading } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtDate } from "@/lib/format";
import type { Brief, Timeline } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function KeyMoments({ matterId, brief, showAll: initial = false }: { matterId: number; brief?: Brief; showAll?: boolean }) {
  const [showAll, setShowAll] = useState(initial);
  const timeline = useApi<Timeline>(showAll ? `/api/matters/${matterId}/timeline` : null);
  const ranked = timeline.data ? [...timeline.data.items].sort((a, b) => (b.importance ?? 0) - (a.importance ?? 0)) : [];
  return (
    <Card>
      <CardHeader className="flex-row items-center pb-1">
        <CardTitle className="text-sm">⭐ Key moments{brief && ` · ${brief.key_moments.length} of ${brief.total_records}`}</CardTitle>
        <Button variant="link" size="sm" className="ml-auto" onClick={() => setShowAll((v) => !v)}>{showAll ? "Top moments only" : "Show all ▸"}</Button>
      </CardHeader>
      <CardContent className="text-sm">
        {!showAll && (
          <ol className="space-y-1">
            {brief?.key_moments.map((k) => (
              <li key={k.rank} className="flex gap-2">
                <span className="w-6 text-right font-mono font-semibold">{k.importance}</span>
                <span className="w-24 shrink-0 font-mono text-xs">{fmtDate(k.date)}</span>
                <span><span className="font-medium">{k.title}</span> <span className="text-muted-foreground">· {k.rank_reason}</span><Chips citations={k.citations} /></span>
              </li>
            ))}
          </ol>
        )}
        {showAll && (timeline.loading ? <Loading /> : (
          <ol className="max-h-[60vh] space-y-1 overflow-y-auto">
            {ranked.map((t) => (
              <li key={t.record_id} className="flex gap-2">
                <span className="w-6 text-right font-mono">{t.importance ?? "–"}</span>
                <span className="w-24 shrink-0 font-mono text-xs">{fmtDate(t.occurred_at)}</span>
                <span>{t.one_liner ?? t.title}<Chips citations={t.citations} /></span>
              </li>
            ))}
          </ol>
        ))}
      </CardContent>
    </Card>
  );
}
