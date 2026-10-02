import { Chips } from "@/components/citations/CitationChip";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtDate } from "@/lib/format";
import type { DeadlineItem, Deadlines } from "@/lib/types";

export function DeadlinesBoard({ deadlines }: { deadlines?: Deadlines }) {
  const cols: [string, DeadlineItem[]][] = [["⏰ Overdue", deadlines?.overdue ?? []], ["Coming", deadlines?.upcoming ?? []], ["Waiting on", deadlines?.waiting_on ?? []]];
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">Overdue · Coming · Waiting on</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-3 gap-2 text-xs">
        {cols.map(([title, items]) => (
          <div key={title}>
            <p className="mb-1 font-medium">{title} ({items.length})</p>
            <ul className="space-y-1">
              {items.map((d) => (
                <li key={d.id} className={d.overdue ? "text-destructive" : ""}>
                  {d.due_at && <span className="font-mono">{fmtDate(d.due_at)} </span>}{d.title}
                  {d.waiting_on && <span className="text-muted-foreground"> · {d.waiting_on}</span>}
                  <Chips citations={d.citations} />
                </li>
              ))}
            </ul>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
