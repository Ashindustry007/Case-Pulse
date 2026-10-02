import { Cited } from "@/components/citations/Cited";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Brief } from "@/lib/types";

const ROWS = [["carrier", "Carrier"], ["bi_per_person", "BI per person"], ["bi_per_accident", "BI per accident"], ["um_uim", "UM/UIM"], ["medpay", "MedPay"]] as const;

export function CoverageTile({ coverage }: { coverage: Brief["coverage"] }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">Coverage</CardTitle></CardHeader>
      <CardContent>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
          {ROWS.map(([k, label]) => (
            <div key={k} className="contents"><dt className="text-muted-foreground">{label}</dt><dd><Cited value={coverage[k]} /></dd></div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
