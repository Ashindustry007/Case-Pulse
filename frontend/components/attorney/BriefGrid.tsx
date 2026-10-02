"use client";
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
    <div className="space-y-4">
      {b.stale && <p className="text-xs text-amber-700">Records changed since the last digest; some facts may be out of date.</p>}
      <div className="grid grid-cols-2 gap-4"><WorthTile worth={b.worth} /><CoverageTile coverage={b.coverage} /></div>
      <div className="grid grid-cols-[1fr_1.4fr_1.4fr] gap-4">
        <SpendTile costs={costs.data} /><DeadlinesBoard deadlines={deadlines.data} /><StorySoFar story={b.story} />
      </div>
      <KeyMoments matterId={matterId} brief={b} />
      <div className="grid grid-cols-2 gap-4">
        <InjuriesPanel injuries={b.injuries} />
        <ProvidersPanel matterId={matterId} providers={providers.data} grants={grants.data} />
      </div>
    </div>
  );
}
