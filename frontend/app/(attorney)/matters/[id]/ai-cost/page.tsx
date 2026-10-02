"use client";
import { use } from "react";
import { AiCostTab } from "@/components/attorney/AiCostTab";
import { MatterPage } from "@/components/attorney/MatterNav";

export default function AiCostPage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  return (
    <MatterPage title="AI cost" subtitle="Every model run on this matter: what it did, which model, and what it cost.">
      <AiCostTab matterId={matterId} />
    </MatterPage>
  );
}
