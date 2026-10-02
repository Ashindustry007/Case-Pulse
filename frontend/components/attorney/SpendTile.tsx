"use client";
import { Area, AreaChart, ResponsiveContainer, Tooltip } from "recharts";
import { Chips } from "@/components/citations/CitationChip";
import { Cited } from "@/components/citations/Cited";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtMoney } from "@/lib/format";
import type { Costs } from "@/lib/types";

export function SpendTile({ costs }: { costs?: Costs }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">Firm spend</CardTitle></CardHeader>
      <CardContent className="space-y-1 text-sm">
        {costs && <p className="text-lg font-semibold"><Cited value={costs.total} render={(v: number) => fmtMoney(v)} /></p>}
        {costs && costs.monthly.length > 1 && (
          <div className="h-12"><ResponsiveContainer><AreaChart data={costs.monthly}>
            <Tooltip formatter={(v) => fmtMoney(Number(v ?? 0))} labelFormatter={(_, p) => p?.[0]?.payload?.month ?? ""} />
            <Area dataKey="amount" stroke="var(--primary)" fill="var(--primary)" fillOpacity={0.15} />
          </AreaChart></ResponsiveContainer></div>
        )}
        <ul className="text-xs">{costs?.by_category.map((c) => <li key={c.category}>{c.category}: {fmtMoney(c.amount)}<Chips citations={c.citations} /></li>)}</ul>
      </CardContent>
    </Card>
  );
}
