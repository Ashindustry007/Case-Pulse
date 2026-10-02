import { Stethoscope } from "lucide-react";
import { Chips } from "@/components/citations/CitationChip";
import { Panel, Section } from "@/components/common/Section";
import type { Brief } from "@/lib/types";

/** Generic body regions → SVG rects on a simple figure (no case data). */
const REGIONS: Record<string, [number, number, number, number]> = {
  head: [40, 0, 20, 20], neck: [44, 20, 12, 8], shoulder: [25, 28, 50, 8], chest: [32, 36, 36, 20],
  back: [32, 36, 36, 34], lumbar: [34, 58, 32, 12], arm: [16, 36, 12, 40], hand: [12, 76, 12, 10],
  hip: [32, 70, 36, 10], leg: [34, 80, 32, 50], knee: [34, 102, 32, 8], foot: [34, 130, 32, 8],
};
const regionOf = (r?: string | null) => Object.keys(REGIONS).find((k) => (r ?? "").toLowerCase().includes(k)) ?? null;
const TIER: Record<string, string> = { soft_tissue: "text-muted-foreground", objective: "text-warning", surgical: "text-danger" };

export function InjuriesPanel({ injuries }: { injuries: Brief["injuries"] }) {
  const hit = new Set(injuries.map((i) => regionOf(i.body_region ?? i.name)).filter(Boolean));
  return (
    <Section icon={Stethoscope} title="Injuries">
      <Panel className="flex gap-5">
        <svg viewBox="0 0 100 140" className="h-36 w-20 shrink-0" aria-label="Body map">
          {Object.entries(REGIONS).map(([k, [x, y, w, h]]) => (
            <rect key={k} x={x} y={y} width={w} height={h} rx={3} className={hit.has(k) ? "fill-warning/70" : "fill-muted"} />
          ))}
        </svg>
        <ul className="min-w-0 flex-1 space-y-3">
          {injuries.length === 0 && <li className="text-muted-foreground">No injuries documented yet.</li>}
          {injuries.map((i) => (
            <li key={i.name} className="text-[13.5px] leading-snug">
              <span className={i.primary ? "font-semibold" : "font-medium"}>{i.name}</span>
              {i.severity_tier && <span className={`ml-2 text-[11px] uppercase tracking-wider ${TIER[i.severity_tier] ?? ""}`}>{i.severity_tier.replace("_", " ")}</span>}
              <Chips citations={i.citations} />
              {i.description && <p className="mt-0.5 text-[13px] text-muted-foreground">{i.description}</p>}
            </li>
          ))}
        </ul>
      </Panel>
    </Section>
  );
}
