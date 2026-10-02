"use client";
import { Chips } from "@/components/citations/CitationChip";
import { useApi } from "@/lib/use-api";
import type { Timeline } from "@/lib/types";
export default function Page() {
  const { data } = useApi<Timeline>("/api/matters/1001/timeline");
  return <div className="p-8">{data?.items.map((i) => <div key={i.record_id}>{i.title}<Chips citations={i.citations} /></div>)}</div>;
}
