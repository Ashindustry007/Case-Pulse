import { Chips } from "@/components/citations/CitationChip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Brief } from "@/lib/types";

export function StorySoFar({ story }: { story: Brief["story"] }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">📝 Story so far</CardTitle></CardHeader>
      <CardContent><ul className="list-disc space-y-1 pl-4 text-sm">{story.map((s, i) => <li key={i}>{s.text}<Chips citations={s.citations} /></li>)}</ul></CardContent>
    </Card>
  );
}
