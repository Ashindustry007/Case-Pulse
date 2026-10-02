"use client";
import { MessageSquare, Share2 } from "lucide-react";
import Link from "next/link";
import { use, useState } from "react";
import { AiCostTab } from "@/components/attorney/AiCostTab";
import { AskPanel } from "@/components/attorney/AskPanel";
import { BriefGrid } from "@/components/attorney/BriefGrid";
import { KeyMoments } from "@/components/attorney/KeyMoments";
import { MatterHeader } from "@/components/attorney/MatterHeader";
import { SinceLastVisit } from "@/components/attorney/SinceLastVisit";
import { ErrorNote, Loading } from "@/components/common/states";
import { Button, buttonVariants } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Overview } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const TAB = "flex-none rounded-none px-3 text-[13px]";

export default function MatterPage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  const overview = useApi<Overview>(`/api/matters/${matterId}/overview`);
  // One AskPanel stays mounted (so a conversation survives collapsing): a column on wide screens, a slide-over below.
  const [askOpen, setAskOpen] = useState(false);       // slide-over (< xl)
  const [askHidden, setAskHidden] = useState(false);   // collapsed column (>= xl)
  return (
    <div className={`grid h-[calc(100dvh-3rem)] ${askHidden ? "xl:grid-cols-1" : "xl:grid-cols-[minmax(0,1fr)_390px]"}`}>
      <main className="min-w-0 overflow-y-auto">
        <div className="mx-auto max-w-[1080px] space-y-6 px-4 py-6 sm:px-6">
          <ErrorNote error={overview.error} />
          {overview.data ? <MatterHeader overview={overview.data} /> : <Loading lines={5} />}
          <Tabs defaultValue="brief" className="gap-6">
            <div className="flex items-center gap-3 border-b">
              <TabsList variant="line" className="h-10 gap-1 p-0">
                <TabsTrigger value="brief" className={TAB}>Brief</TabsTrigger>
                <TabsTrigger value="deep" className={TAB}>Deep-Dive</TabsTrigger>
                <TabsTrigger value="cost" className={TAB}>AI cost</TabsTrigger>
              </TabsList>
              <Link href={`/matters/${matterId}/share`} className={buttonVariants({ size: "sm", className: "mb-1 ml-auto" })}>
                <Share2 /> <span className="hidden sm:inline">Share with provider</span><span className="sm:hidden">Share</span>
              </Link>
            </div>
            <TabsContent value="brief" className="space-y-8"><SinceLastVisit matterId={matterId} /><BriefGrid matterId={matterId} /></TabsContent>
            <TabsContent value="deep"><KeyMoments matterId={matterId} showAll /></TabsContent>
            <TabsContent value="cost"><AiCostTab matterId={matterId} /></TabsContent>
          </Tabs>
        </div>
      </main>

      <aside
        aria-label="Ask the case"
        className={`fixed inset-y-12 right-0 z-30 w-[min(420px,100vw)] border-l bg-background shadow-2xl transition-transform duration-200 xl:static xl:z-auto xl:w-auto xl:translate-x-0 xl:shadow-none ${askOpen ? "translate-x-0" : "translate-x-full"} ${askHidden ? "xl:hidden" : ""}`}
      >
        <AskPanel matterId={matterId} onClose={() => (askOpen ? setAskOpen(false) : setAskHidden(true))} />
      </aside>

      {(askHidden || !askOpen) && (
        <Button
          size="lg" aria-label="Open Ask the case"
          className={`fixed bottom-5 right-5 z-20 h-10 gap-2 rounded-full px-4 shadow-lg ${askHidden ? "" : "xl:hidden"}`}
          onClick={() => { setAskOpen(true); setAskHidden(false); }}
        >
          <MessageSquare /> Ask the case
        </Button>
      )}
    </div>
  );
}
