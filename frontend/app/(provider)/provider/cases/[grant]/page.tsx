"use client";
import { use } from "react";
import { toast } from "sonner";
import { ErrorNote, Loading } from "@/components/common/states";
import { ProviderCaseView } from "@/components/provider/ProviderCaseView";
import { api, apiUrl } from "@/lib/api";
import type { ProviderCase } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function ProviderCasePage({ params }: { params: Promise<{ grant: string }> }) {
  const grant = Number(use(params).grant);
  const { data, error, reload } = useApi<ProviderCase>(`/api/provider/cases/${grant}`);
  if (error) return <ErrorNote error={error.status === 404 ? { message: "This case is no longer shared with you." } : error} />;
  if (!data) return <Loading lines={8} />;
  return (
    <ProviderCaseView
      c={data}
      docHref={(id) => apiUrl(`/api/provider/cases/${grant}/documents/${encodeURIComponent(id)}`)}
      onMarkSent={async (id) => {
        await api(`/api/provider/requests/${encodeURIComponent(id)}/complete`, { method: "POST" });
        toast.success("Marked as sent — the firm can see it.");
        reload();
      }}
    />
  );
}
