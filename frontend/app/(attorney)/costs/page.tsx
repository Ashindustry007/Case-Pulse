"use client";
import Link from "next/link";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { ErrorNote, Loading } from "@/components/common/states";
import { usd } from "@/lib/format";
import type { FirmCostReport } from "@/lib/types";
import { useApi } from "@/lib/use-api";

export default function FirmCosts() {
  const { data, error } = useApi<FirmCostReport>("/api/ai-costs/firm?days=30");
  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8 sm:px-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI cost</h1>
        <p className="mt-1 text-[13px] text-muted-foreground">Last 30 days{data && ` · ${usd(data.total_usd)} total`}</p>
      </div>
      <ErrorNote error={error} />
      {!data ? <Loading /> : (
        <>
          <div className="h-44 rounded-xl border bg-card p-3"><ResponsiveContainer><LineChart data={data.series}>
            <XAxis dataKey="date" fontSize={10} stroke="var(--muted-foreground)" tickLine={false} axisLine={false} /><Tooltip formatter={(v) => usd(Number(v ?? 0))} contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <Line dataKey="usd" stroke="var(--primary)" strokeWidth={2} dot={false} />
          </LineChart></ResponsiveContainer></div>
          <ul className="divide-y rounded-xl border bg-card text-sm">
            {data.matters.map((m) => (
              <li key={m.matter_id} className="flex px-4 py-3">
                <Link className="hover:text-primary hover:underline" href={`/matters/${m.matter_id}`}>{m.display_number} {m.description}</Link>
                <span className="ml-auto">{usd(m.total_usd)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
