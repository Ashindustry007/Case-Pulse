"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, use } from "react";
import { ShareComposer } from "@/components/attorney/ShareComposer";

function Inner({ matterId }: { matterId: number }) {
  const p = useSearchParams().get("provider");
  return <ShareComposer matterId={matterId} initialProvider={p ? Number(p) : undefined} />;
}

export default function SharePage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  return <Suspense><Inner matterId={matterId} /></Suspense>;
}
