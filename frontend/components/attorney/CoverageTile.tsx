import { ShieldCheck } from "lucide-react";
import { Cited } from "@/components/citations/Cited";
import { KpiTile } from "@/components/common/Stat";
import { fmtMoneyShort } from "@/lib/format";
import { isNotFound, type Brief } from "@/lib/types";

const ROWS = [["carrier", "Carrier"], ["bi_per_person", "BI / person"], ["bi_per_accident", "BI / accident"], ["um_uim", "UM / UIM"], ["medpay", "MedPay"]] as const;

/** "$100,000" → "$100k" for the headline; anything unparsable is shown as written. */
const short = (v: string) => { const n = Number(v.replace(/[^0-9.]/g, "")); return n >= 1000 && /^\$?\s*[\d,]+(\.\d+)?$/.test(v.trim()) ? fmtMoneyShort(n) : v; };

export function CoverageTile({ coverage }: { coverage: Brief["coverage"] }) {
  const person = isNotFound(coverage.bi_per_person) ? null : coverage.bi_per_person.value;
  const accident = isNotFound(coverage.bi_per_accident) ? null : coverage.bi_per_accident.value;
  const headline = person || accident
    ? <span>{person ? short(person) : "—"}<span className="text-muted-foreground"> / </span>{accident ? short(accident) : "—"}</span>
    : <span className="text-lg font-medium text-muted-foreground">No limits found</span>;
  return (
    <KpiTile icon={ShieldCheck} label="Coverage" tag={coverage.confirmed ? "Confirmed" : undefined} value={headline}>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
        {ROWS.map(([k, label]) => (
          <div key={k} className="contents"><dt>{label}</dt><dd className="min-w-0 text-foreground"><Cited value={coverage[k]} /></dd></div>
        ))}
      </dl>
    </KpiTile>
  );
}
