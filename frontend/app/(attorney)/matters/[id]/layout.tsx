"use client";
import { use } from "react";
import { MatterSidebar, MatterTabsMobile } from "@/components/attorney/MatterNav";

export default function MatterLayout({ children, params }: { children: React.ReactNode; params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  return (
    <div className="flex h-[calc(100dvh-3rem)]">
      <MatterSidebar matterId={matterId} />
      <div className="flex min-w-0 flex-1 flex-col">
        <MatterTabsMobile matterId={matterId} />
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </div>
    </div>
  );
}
