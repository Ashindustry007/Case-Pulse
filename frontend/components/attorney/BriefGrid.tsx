"use client";
import { Gauge, TriangleAlert } from "lucide-react";
import { Section } from "@/components/common/Section";
import { ErrorNote, Loading } from "@/components/common/states";
import type { Brief, Costs, Deadlines, Grant, Providers } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { CoverageTile } from "./CoverageTile";
import { DeadlinesBoard } from "./DeadlinesBoard";
import { InjuriesPanel } from "./InjuriesPanel";
import { KeyMoments } from "./KeyMoments";
import { ProvidersPanel } from "./ProvidersPanel";
import { SpendTile } from "./SpendTile";
import { StorySoFar } from "./StorySoFar";
import { WorthTile } from "./WorthTile";

/** The brief in clusters: key numbers → story (+ deadlines, injuries) → key moments → providers. */
export function BriefGrid({ matterId }: { matterId: number }) {
  const brief = useApi<Brief>(`/api/matters/${matterId}/brief`);
  const costs = useApi<Costs>(`/api/matters/${matterId}/costs`);
  const deadlines = useApi<Deadlines>(`/api/matters/${matterId}/deadlines`);
  const providers = useApi<Providers>(`/api/matters/${matterId}/providers`);
  const grants = useApi<Grant[]>(`/api/matters/${matterId}/shares`);
  if (brief.error) return <ErrorNote error={brief.error} />;
  if (!brief.data) return <Loading lines={10} />;
  const b = brief.data;
  return (
    <div className="space-y-8">
      {b.stale && (
        <p className="flex items-center gap-2 rounded-lg bg-warning/10 px-3 py-2 text-[13px] text-warning">
          <TriangleAlert className="size-4 shrink-0" /> Records changed since the last digest; some facts may be out of date.
        </p>
      )}
      <Section icon={Gauge} title="Key numbers">
        <div className="grid gap-4 md:grid-cols-3"><WorthTile worth={b.worth} /><CoverageTile coverage={b.coverage} /><SpendTile costs={costs.data} /></div>
      </Section>
      <div className="grid items-start gap-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <StorySoFar story={b.story} />
        <div className="space-y-8"><DeadlinesBoard deadlines={deadlines.data} /><InjuriesPanel injuries={b.injuries} /></div>
      </div>
      <KeyMoments matterId={matterId} brief={b} />
      <ProvidersPanel matterId={matterId} providers={providers.data} grants={grants.data} />
    </div>
  );
}
