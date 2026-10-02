"use client";
import { Wallet } from "lucide-react";
import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";
import { Chips } from "@/components/citations/CitationChip";
import { Cited } from "@/components/citations/Cited";
import { KpiTile } from "@/components/common/Stat";
import { Skeleton } from "@/components/ui/skeleton";
import { fmtMoney } from "@/lib/format";
import type { Costs } from "@/lib/types";

export function SpendTile({ costs }: { costs?: Costs }) {
  if (!costs) return <KpiTile icon={Wallet} label="Firm spend" value={<Skeleton className="h-8 w-28" />} />;
  const top = costs.by_category.slice(0, 4);
  return (
    <KpiTile icon={Wallet} label="Firm spend" value={<Cited value={costs.total} render={(v: number) => fmtMoney(v)} />}>
      {costs.monthly.length > 1 && (
        <div className="h-10 w-full"><ResponsiveContainer>
          <AreaChart data={costs.monthly}>
            <Tooltip formatter={(v) => fmtMoney(Number(v ?? 0))} labelFormatter={(_, p) => p?.[0]?.payload?.month ?? ""}
              contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} />
            <Area dataKey="amount" stroke="var(--primary)" strokeWidth={1.5} fill="var(--primary)" fillOpacity={0.14} />
          </AreaChart>
        </ResponsiveContainer></div>
      )}
      <ul className="space-y-1">
        {top.map((c) => (
          <li key={c.category} className="flex items-baseline justify-between gap-3">
            <span className="min-w-0">{c.category}<Chips citations={c.citations} /></span>
            <span className="shrink-0 text-foreground">{fmtMoney(c.amount)}</span>
          </li>
        ))}
        {costs.by_category.length > top.length && <li className="text-xs">+{costs.by_category.length - top.length} more categories</li>}
      </ul>
    </KpiTile>
  );
}
