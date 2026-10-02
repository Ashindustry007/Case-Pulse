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
    <div className="mx-auto max-w-4xl space-y-4 p-6">
      <h1 className="text-xl font-semibold">AI cost · last 30 days {data && `· ${usd(data.total_usd)}`}</h1>
      <ErrorNote error={error} />
      {!data ? <Loading /> : (
        <>
          <div className="h-40"><ResponsiveContainer><LineChart data={data.series}>
            <XAxis dataKey="date" fontSize={10} /><Tooltip formatter={(v) => usd(Number(v ?? 0))} />
            <Line dataKey="usd" stroke="var(--primary)" dot={false} />
          </LineChart></ResponsiveContainer></div>
          <ul className="divide-y rounded border text-sm">
            {data.matters.map((m) => (
              <li key={m.matter_id} className="flex p-2">
                <Link className="underline" href={`/matters/${m.matter_id}`}>{m.display_number} {m.description}</Link>
                <span className="ml-auto font-mono">{usd(m.total_usd)}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
