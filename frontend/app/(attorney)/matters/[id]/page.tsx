"use client";
import { ArrowUp, MessageSquare, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { use, useState } from "react";
import { CostPill } from "@/components/attorney/CostPill";
import { DeadlinesBoard } from "@/components/attorney/DeadlinesBoard";
import { MatterHeader } from "@/components/attorney/MatterHeader";
import { OverviewKpis } from "@/components/attorney/OverviewKpis";
import { SinceLastVisit } from "@/components/attorney/SinceLastVisit";
import { Panel, Section } from "@/components/common/Section";
import { ErrorNote, Loading } from "@/components/common/states";
import { Button } from "@/components/ui/button";
import type { Brief, Deadlines, Overview, SuggestedQuestions } from "@/lib/types";
import { useApi } from "@/lib/use-api";

/** Overview = the 90-second read: who/where, four numbers, what changed, what's due. Everything else has its own page. */
export default function MatterOverviewPage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  const overview = useApi<Overview>(`/api/matters/${matterId}/overview`);
  const brief = useApi<Brief>(`/api/matters/${matterId}/brief`);
  const deadlines = useApi<Deadlines>(`/api/matters/${matterId}/deadlines`);
  return (
    <div className="mx-auto max-w-[1180px] space-y-6 px-4 py-6 sm:px-6">
      <ErrorNote error={overview.error ?? brief.error} />
      {overview.data ? <MatterHeader overview={overview.data} /> : <Loading lines={3} />}
      {brief.data?.stale && (
        <p className="flex items-center gap-2 rounded-lg bg-warning/10 px-3 py-2 text-[13px] text-warning">
          <TriangleAlert className="size-4 shrink-0" /> Records changed since the last digest; some facts may be out of date.
        </p>
      )}
      <OverviewKpis overview={overview.data} brief={brief.data} matterId={matterId} />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <SinceLastVisit matterId={matterId} />
        <div className="space-y-6">
          <DeadlinesBoard deadlines={deadlines.data} />
          <QuickAsk matterId={matterId} />
        </div>
      </div>
      <CostPill matterId={matterId} lastSyncedAt={overview.data?.last_synced_at} />
    </div>
  );
}

/** Small entry point into the full Ask page; the question is carried in the URL. */
function QuickAsk({ matterId }: { matterId: number }) {
  const router = useRouter();
  const ideas = useApi<SuggestedQuestions>(`/api/matters/${matterId}/suggested-questions`).data?.questions ?? [];
  const [q, setQ] = useState("");
  const go = (question: string) => router.push(`/matters/${matterId}/ask${question.trim() ? `?q=${encodeURIComponent(question.trim())}` : ""}`);
  return (
    <Section icon={MessageSquare} title="Ask the case">
      <Panel className="space-y-3">
        <form onSubmit={(e) => { e.preventDefault(); go(q); }} className="flex items-center gap-2 rounded-xl border bg-background py-1 pl-3 pr-1 focus-within:border-ring">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask anything — answers are cited" aria-label="Ask the case"
            className="h-8 min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-muted-foreground" />
          <Button type="submit" size="icon" className="rounded-lg" aria-label="Ask"><ArrowUp className="size-4" /></Button>
        </form>
        {ideas.slice(0, 2).map((x) => (
          <button key={x} type="button" onClick={() => go(x)} className="block w-full text-left text-[13px] leading-snug text-muted-foreground hover:text-primary">
            <span className="line-clamp-1">↳ {x}</span>
          </button>
        ))}
      </Panel>
    </Section>
  );
}
