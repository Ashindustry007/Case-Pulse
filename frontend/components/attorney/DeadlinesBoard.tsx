"use client";
import { CalendarClock } from "lucide-react";
import { useState } from "react";
import { Chips } from "@/components/citations/CitationChip";
import { Panel, Section } from "@/components/common/Section";
import { fmtDate } from "@/lib/format";
import type { DeadlineItem, Deadlines } from "@/lib/types";

type Key = "overdue" | "upcoming" | "waiting_on";
const TABS: [Key, string][] = [["overdue", "Overdue"], ["upcoming", "Upcoming"], ["waiting_on", "Waiting on"]];
const SHOWN = 6;

/** Overdue / upcoming / waiting-on as ONE list behind a segmented control (was three cramped columns). */
export function DeadlinesBoard({ deadlines }: { deadlines?: Deadlines }) {
  const [picked, setPicked] = useState<Key | null>(null);
  const [all, setAll] = useState(false);
  const data: Record<Key, DeadlineItem[]> = { overdue: deadlines?.overdue ?? [], upcoming: deadlines?.upcoming ?? [], waiting_on: deadlines?.waiting_on ?? [] };
  const tab = picked ?? (TABS.find(([k]) => data[k].length)?.[0] ?? "overdue");
  const items = data[tab];
  const visible = all ? items : items.slice(0, SHOWN);
  return (
    <Section icon={CalendarClock} title="Deadlines">
      <Panel className="space-y-3">
        <div role="tablist" className="inline-flex rounded-lg bg-muted p-0.5 text-[13px]">
          {TABS.map(([k, label]) => (
            <button
              key={k} role="tab" type="button" aria-selected={tab === k}
              onClick={() => { setPicked(k); setAll(false); }}
              className={`rounded-md px-3 py-1 transition-colors ${tab === k ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}
            >
              {label} <span className={k === "overdue" && data[k].length ? "text-danger" : "text-muted-foreground"}>{data[k].length}</span>
            </button>
          ))}
        </div>
        {items.length === 0 ? <p className="py-2 text-muted-foreground">Nothing here.</p> : (
          <ul className="divide-y">
            {visible.map((d) => (
              <li key={d.id} className="grid grid-cols-[5.25rem_1fr] gap-3 py-2 text-[13.5px] first:pt-0">
                <span className={`pt-px text-xs ${d.overdue ? "text-danger" : "text-muted-foreground"}`}>{d.due_at ? fmtDate(d.due_at) : "—"}</span>
                <span className="min-w-0 leading-snug">
                  {d.title}
                  {d.waiting_on && tab !== "waiting_on" && <span className="text-muted-foreground"> · {d.waiting_on}</span>}
                  {d.assignee && <span className="text-muted-foreground"> · {d.assignee}</span>}
                  <Chips citations={d.citations} />
                </span>
              </li>
            ))}
          </ul>
        )}
        {items.length > SHOWN && (
          <button type="button" className="text-xs text-primary hover:underline" onClick={() => setAll((v) => !v)}>
            {all ? "Show fewer" : `Show ${items.length - SHOWN} more`}
          </button>
        )}
      </Panel>
    </Section>
  );
}
