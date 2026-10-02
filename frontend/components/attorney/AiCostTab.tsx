"use client";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ErrorNote, Loading } from "@/components/common/states";
import { Card, CardContent } from "@/components/ui/card";
import { fmtDateTime, usd } from "@/lib/format";
import type { AiCostReport } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const SHADES = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];
const tok = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n));

export function AiCostTab({ matterId }: { matterId: number }) {
  const { data: r, error } = useApi<AiCostReport>(`/api/ai-costs?matter_id=${matterId}`);
  if (error) return <ErrorNote error={error} />;
  if (!r) return <Loading lines={6} />;
  const row = [{ name: "cost", ...Object.fromEntries(r.by_purpose.map((p) => [p.key, p.usd])) }];
  return (
    <div className="space-y-3 text-sm">
      {r.budget_pct != null && r.budget_pct >= 80 && (
        <div className="rounded border border-amber-400 bg-amber-50 p-2 text-amber-900 dark:bg-amber-950 dark:text-amber-200">
          AI spend is at {r.budget_pct.toFixed(0)}% of this matter&apos;s {usd(r.budget_usd ?? 0)} budget. Nothing is blocked.
        </div>
      )}
      <Card><CardContent className="space-y-2 pt-4">
        <p className="flex flex-wrap gap-x-6">
          <b>Total {usd(r.total_usd)}</b>
          <span>One-time digestion {usd(r.one_time_usd)}</span>
          <span>Ongoing {usd(r.ongoing_usd)} ({r.ask_count} Asks, ≈{usd(r.avg_ask_usd)} ea)</span>
          {r.budget_usd != null && <span className="text-muted-foreground">budget {usd(r.budget_usd)} · {r.budget_pct?.toFixed(0)}% used</span>}
        </p>
        <div className="h-14"><ResponsiveContainer>
          <BarChart data={row} layout="vertical" margin={{ left: 0, right: 0 }}>
            <XAxis type="number" hide /><YAxis type="category" dataKey="name" hide />
            <Tooltip formatter={(v, k) => [usd(Number(v ?? 0)), String(k)]} />
            {r.by_purpose.map((p, i) => <Bar key={p.key} dataKey={p.key} stackId="a" fill={SHADES[i % SHADES.length]} />)}
          </BarChart>
        </ResponsiveContainer></div>
        <p className="text-xs text-muted-foreground">{r.by_purpose.map((p) => `${p.key} ${usd(p.usd)}`).join(" · ")}</p>
        <p>Saved by cache: <b>{usd(r.cache_savings_usd)}</b></p>
      </CardContent></Card>
      <Card><CardContent className="pt-4">
        <table className="w-full text-xs">
          <thead className="text-left text-muted-foreground"><tr><th>Time</th><th>User</th><th>Purpose</th><th>Model</th><th>Tokens in / out</th><th className="text-right">$</th></tr></thead>
          <tbody>
            {r.runs.map((x, i) => (
              <tr key={i} className="border-t">
                <td>{fmtDateTime(x.at)}</td><td>{x.user ?? "system"}</td><td>{x.purpose}</td><td>{x.model}</td>
                <td>{tok(x.input_tokens)} / {tok(x.output_tokens)}</td>
                <td className="text-right font-mono">{x.cache_hit ? "cache hit $0.00" : usd(x.cost_usd)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent></Card>
    </div>
  );
}
