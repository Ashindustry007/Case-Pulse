import { Chips } from "@/components/citations/CitationChip";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Brief } from "@/lib/types";

/** Generic body regions → SVG rects on a simple figure (no case data). */
const REGIONS: Record<string, [number, number, number, number]> = {
  head: [40, 0, 20, 20], neck: [44, 20, 12, 8], shoulder: [25, 28, 50, 8], chest: [32, 36, 36, 20],
  back: [32, 36, 36, 34], lumbar: [34, 58, 32, 12], arm: [16, 36, 12, 40], hand: [12, 76, 12, 10],
  hip: [32, 70, 36, 10], leg: [34, 80, 32, 50], knee: [34, 102, 32, 8], foot: [34, 130, 32, 8],
};
const regionOf = (r?: string | null) => Object.keys(REGIONS).find((k) => (r ?? "").toLowerCase().includes(k)) ?? null;

export function InjuriesPanel({ injuries }: { injuries: Brief["injuries"] }) {
  const hit = new Set(injuries.map((i) => regionOf(i.body_region ?? i.name)).filter(Boolean));
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">🩺 Injuries</CardTitle></CardHeader>
      <CardContent className="flex gap-4 text-sm">
        <svg viewBox="0 0 100 140" className="h-40 w-24 shrink-0" aria-label="Body map">
          {Object.entries(REGIONS).map(([k, [x, y, w, h]]) => (
            <rect key={k} x={x} y={y} width={w} height={h} rx={3} className={hit.has(k) ? "fill-destructive/70" : "fill-muted"} />
          ))}
        </svg>
        <ul className="space-y-1">
          {injuries.map((i) => (
            <li key={i.name}>
              <span className={i.primary ? "font-semibold" : ""}>{i.name}</span>
              {i.severity_tier && <Badge variant="outline" className="ml-1 text-[10px]">{i.severity_tier.replace("_", " ")}</Badge>}
              <Chips citations={i.citations} />
              {i.description && <p className="text-xs text-muted-foreground">{i.description}</p>}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
