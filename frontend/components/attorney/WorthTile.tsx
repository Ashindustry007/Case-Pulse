import { Chips } from "@/components/citations/CitationChip";
import { NotFoundText } from "@/components/common/states";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtMoneyShort } from "@/lib/format";
import { isNotFound, type Brief } from "@/lib/types";

export function WorthTile({ worth }: { worth: Brief["worth"] }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">Case worth <Badge variant="outline">Estimate</Badge></CardTitle></CardHeader>
      <CardContent className="space-y-1 text-sm">
        {isNotFound(worth) ? <NotFoundText /> : (
          <>
            <p className="text-2xl font-semibold">{fmtMoneyShort(worth.low)} – {fmtMoneyShort(worth.high)}</p>
            <ul className="space-y-0.5">
              {worth.assumptions.map((a) => (
                <li key={a.label}>• {a.label}: {a.not_found ? <NotFoundText /> : a.text}<Chips citations={a.citations} /></li>
              ))}
            </ul>
            {worth.cap_note && <p className="text-amber-700 dark:text-amber-400">{worth.cap_note}</p>}
            <details className="text-xs text-muted-foreground"><summary>Why this range?</summary>{worth.method}</details>
          </>
        )}
      </CardContent>
    </Card>
  );
}
