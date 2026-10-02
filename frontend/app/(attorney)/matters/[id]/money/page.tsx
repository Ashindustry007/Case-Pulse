"use client";
import { use } from "react";
import { CoverageTile } from "@/components/attorney/CoverageTile";
import { MatterPage } from "@/components/attorney/MatterNav";
import { SpendTile } from "@/components/attorney/SpendTile";
import { WorthTile } from "@/components/attorney/WorthTile";
import { ErrorNote, Loading } from "@/components/common/states";
import type { Brief, Costs } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function MoneyPage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  const brief = useApi<Brief>(`/api/matters/${matterId}/brief`);
  const costs = useApi<Costs>(`/api/matters/${matterId}/costs`);
  return (
    <MatterPage title="Money" subtitle="What the case may be worth, the coverage behind it, and what the firm has spent.">
      <ErrorNote error={brief.error} />
      {!brief.data ? <Loading lines={8} /> : (
        <div className="grid items-start gap-4 lg:grid-cols-3">
          <WorthTile worth={brief.data.worth} />
          <CoverageTile coverage={brief.data.coverage} />
          <SpendTile costs={costs.data} />
        </div>
      )}
    </MatterPage>
  );
}
