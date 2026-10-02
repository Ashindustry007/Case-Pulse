import { Scale } from "lucide-react";
import { Chips } from "@/components/citations/CitationChip";
import { KpiTile } from "@/components/common/Stat";
import { NotFoundText } from "@/components/common/states";
import { fmtMoneyShort } from "@/lib/format";
import { isNotFound, type Brief } from "@/lib/types";

export function WorthTile({ worth }: { worth: Brief["worth"] }) {
  if (isNotFound(worth)) return <KpiTile icon={Scale} label="Case worth" tag="Estimate" value={<NotFoundText />} />;
  return (
    <KpiTile icon={Scale} label="Case worth" tag="Estimate" value={<span className="text-primary">{fmtMoneyShort(worth.low)} – {fmtMoneyShort(worth.high)}</span>}>
      <ul className="space-y-1.5">
        {worth.assumptions.map((a) => (
          <li key={a.label} className="leading-snug">
            <span className="font-medium text-foreground">{a.label}</span>{" "}
            {a.not_found ? <NotFoundText /> : a.text}<Chips citations={a.citations} />
          </li>
        ))}
      </ul>
      {worth.cap_note && <p className="rounded-md bg-warning/10 px-2 py-1.5 text-warning">{worth.cap_note}</p>}
      <details className="text-xs"><summary className="cursor-pointer select-none hover:text-foreground">How this range is calculated</summary><p className="mt-1">{worth.method}</p></details>
    </KpiTile>
  );
}
