"use client";
import Link from "next/link";
import { use } from "react";
import { AiCostTab } from "@/components/attorney/AiCostTab";
import { AskPanel } from "@/components/attorney/AskPanel";
import { BriefGrid } from "@/components/attorney/BriefGrid";
import { KeyMoments } from "@/components/attorney/KeyMoments";
import { MatterHeader } from "@/components/attorney/MatterHeader";
import { SinceLastVisit } from "@/components/attorney/SinceLastVisit";
import { ErrorNote, Loading } from "@/components/common/states";
import { buttonVariants } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Overview } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function MatterPage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  const overview = useApi<Overview>(`/api/matters/${matterId}/overview`);
  return (
    <div className="grid h-[calc(100vh-45px)] grid-cols-[1fr_400px]">
      <main className="space-y-4 overflow-y-auto p-4">
        <ErrorNote error={overview.error} />
        {overview.data ? <MatterHeader overview={overview.data} /> : <Loading />}
        <Tabs defaultValue="brief">
          <div className="flex items-center">
            <TabsList>
              <TabsTrigger value="brief">Brief</TabsTrigger>
              <TabsTrigger value="deep">Deep-Dive</TabsTrigger>
              <TabsTrigger value="cost">AI cost</TabsTrigger>
            </TabsList>
            <Link href={`/matters/${matterId}/share`} className={buttonVariants({ size: "sm", className: "ml-auto" })}>Share ▸</Link>
          </div>
          <TabsContent value="brief" className="space-y-4">
            <SinceLastVisit matterId={matterId} />
            <BriefGrid matterId={matterId} />
          </TabsContent>
          <TabsContent value="deep"><KeyMoments matterId={matterId} showAll /></TabsContent>
          <TabsContent value="cost"><AiCostTab matterId={matterId} /></TabsContent>
        </Tabs>
      </main>
      <aside className="border-l"><AskPanel matterId={matterId} /></aside>
    </div>
  );
}
