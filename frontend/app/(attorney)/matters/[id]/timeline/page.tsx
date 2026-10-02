"use client";
import { use } from "react";
import { CaseTimeline } from "@/components/attorney/CaseTimeline";
import { MatterPage } from "@/components/attorney/MatterNav";
import { StorySoFar } from "@/components/attorney/StorySoFar";
import { ErrorNote } from "@/components/common/states";
import type { Brief, Deadlines, Timeline } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function TimelinePage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  const timeline = useApi<Timeline>(`/api/matters/${matterId}/timeline`);
  const deadlines = useApi<Deadlines>(`/api/matters/${matterId}/deadlines`);
  const brief = useApi<Brief>(`/api/matters/${matterId}/brief`);
  return (
    <MatterPage wide title="Timeline" subtitle="Every note, email, document, task, deadline and calendar entry on the case, each linked to its source.">
      <ErrorNote error={timeline.error ?? deadlines.error} />
      <CaseTimeline
        timeline={timeline.data} deadlines={deadlines.data} brief={brief.data}
        aside={brief.data && <StorySoFar story={brief.data.story} />}
      />
    </MatterPage>
  );
}
