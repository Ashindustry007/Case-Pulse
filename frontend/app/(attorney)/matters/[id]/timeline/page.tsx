"use client";
import { use } from "react";
import { KeyMoments } from "@/components/attorney/KeyMoments";
import { MatterPage } from "@/components/attorney/MatterNav";
import { StorySoFar } from "@/components/attorney/StorySoFar";
import { ErrorNote, Loading } from "@/components/common/states";
import type { Brief } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function TimelinePage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  const brief = useApi<Brief>(`/api/matters/${matterId}/brief`);
  return (
    <MatterPage title="Timeline" subtitle="The story so far and every moment that mattered, each linked to its source.">
      <ErrorNote error={brief.error} />
      {!brief.data ? <Loading lines={10} /> : (
        <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <StorySoFar story={brief.data.story} />
          <KeyMoments matterId={matterId} brief={brief.data} showAll />
        </div>
      )}
    </MatterPage>
  );
}
