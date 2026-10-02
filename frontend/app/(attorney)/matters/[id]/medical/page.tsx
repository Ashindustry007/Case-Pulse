"use client";
import { use } from "react";
import { InjuriesPanel } from "@/components/attorney/InjuriesPanel";
import { MatterPage } from "@/components/attorney/MatterNav";
import { ProvidersPanel } from "@/components/attorney/ProvidersPanel";
import { ErrorNote, Loading } from "@/components/common/states";
import type { Brief, Grant, Providers } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function MedicalPage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  const brief = useApi<Brief>(`/api/matters/${matterId}/brief`);
  const providers = useApi<Providers>(`/api/matters/${matterId}/providers`);
  const grants = useApi<Grant[]>(`/api/matters/${matterId}/shares`);
  return (
    <MatterPage title="Medical" subtitle="Injuries, treating providers, bills and what each provider can see.">
      <ErrorNote error={brief.error} />
      {!brief.data ? <Loading lines={8} /> : (
        <div className="grid items-start gap-8 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <InjuriesPanel injuries={brief.data.injuries} />
          <ProvidersPanel matterId={matterId} providers={providers.data} grants={grants.data} />
        </div>
      )}
    </MatterPage>
  );
}
