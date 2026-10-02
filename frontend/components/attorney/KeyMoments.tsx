"use client";
import { Flag } from "lucide-react";
import { useState } from "react";
import { Chips } from "@/components/citations/CitationChip";
import { Importance } from "@/components/common/ImportanceDot";
import { Panel, Section } from "@/components/common/Section";
import { Loading } from "@/components/common/states";
import { fmtDate } from "@/lib/format";
import type { Brief, Timeline } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export function KeyMoments({ matterId, brief, showAll: initial = false }: { matterId: number; brief?: Brief; showAll?: boolean }) {
  const [showAll, setShowAll] = useState(initial);
  const timeline = useApi<Timeline>(showAll ? `/api/matters/${matterId}/timeline` : null);
  const ranked = timeline.data ? [...timeline.data.items].sort((a, b) => (b.importance ?? 0) - (a.importance ?? 0)) : [];
  return (
    <Section
      icon={Flag}
      title={showAll ? `Everything, ranked${timeline.data ? ` · ${timeline.data.total} entries` : ""}` : `Key moments${brief ? ` · ${brief.key_moments.length} of ${brief.total_records}` : ""}`}
      action={<button type="button" className="text-primary hover:underline" onClick={() => setShowAll((v) => !v)}>{showAll ? "Top moments only" : "Show all"}</button>}
    >
      <Panel className="p-0">
        {!showAll && (
          <ol className="divide-y">
            {brief?.key_moments.map((k) => (
              <li key={k.rank} className="grid grid-cols-[4.75rem_auto_1fr] items-start gap-3 px-4 py-3">
                <span className="pt-0.5 text-xs text-muted-foreground">{fmtDate(k.date)}</span>
                <Importance n={k.importance} />
                <div className="min-w-0">
                  <p className="text-[14px] font-medium leading-snug">{k.title}<Chips citations={k.citations} /></p>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">{k.rank_reason}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
        {showAll && (timeline.loading ? <div className="p-4"><Loading /></div> : (
          <ol className="max-h-[70vh] divide-y overflow-y-auto">
            {ranked.map((t) => (
              <li key={t.record_id} className="grid grid-cols-[4.75rem_auto_1fr] items-start gap-3 px-4 py-2.5">
                <span className="pt-0.5 text-xs text-muted-foreground">{fmtDate(t.occurred_at)}</span>
                <Importance n={t.importance} />
                <p className="min-w-0 text-[13.5px] leading-snug">{t.one_liner ?? t.title}<Chips citations={t.citations} /></p>
              </li>
            ))}
          </ol>
        ))}
      </Panel>
    </Section>
  );
}
