"use client";
import { BookOpen, FileText, Search, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, use, useCallback, useMemo, useState } from "react";
import { AskPanel } from "@/components/attorney/AskPanel";
import { SOURCE_ICON } from "@/components/citations/CitationChip";
import { SourceTarget, SourceView } from "@/components/citations/SourceDrawer";
import { Button } from "@/components/ui/button";
import { shortName, uniqueCitations } from "@/lib/citations";
import { fmtDate } from "@/lib/format";
import type { Citation } from "@/lib/types";

type Group = { id: string; title: string; type: string; date?: string | null; cites: Citation[]; pages: number[] };
type Sel = { list: Citation[]; i: number };

const TYPE: Record<string, string> = {
  note: "Note", communication: "Email", task: "Task", calendar_entry: "Event", document: "Document", expense: "Expense",
  time_entry: "Time entry", bill: "Bill", medical_record: "Medical record", medical_bill: "Medical bill", damage: "Damages",
  custom_field: "Case field", matter_event: "Event", contact: "Contact",
};

/** All citations from the conversation, one row per source record, in first-cited order. */
function groupSources(cites: Citation[]): Group[] {
  const by = new Map<string, Group>();
  for (const c of uniqueCitations(cites)) {
    const g = by.get(c.record_id) ?? { id: c.record_id, title: c.title, type: c.source_type, date: c.date, cites: [], pages: [] };
    g.cites.push(c);
    if (c.page != null && !g.pages.includes(c.page)) g.pages.push(c.page);
    by.set(c.record_id, g);
  }
  return [...by.values()];
}

function AskWorkspace({ matterId }: { matterId: number }) {
  const initial = useSearchParams().get("q") ?? undefined;
  const [cites, setCites] = useState<Citation[]>([]);
  const [sel, setSel] = useState<Sel | null>(null);
  const [filter, setFilter] = useState("");
  const onSources = useCallback((c: Citation[]) => setCites(c), []);
  const open = useCallback((list: Citation[], i = 0) => setSel({ list, i }), []);
  const groups = useMemo(() => groupSources(cites), [cites]);
  const shown = groups.filter((g) => `${g.title} ${TYPE[g.type] ?? ""}`.toLowerCase().includes(filter.toLowerCase()));
  const current = sel?.list[sel.i];

  return (
    <SourceTarget open={open}>
      <div className="grid h-full grid-rows-[minmax(0,1.2fr)_minmax(0,1fr)] lg:grid-cols-2 lg:grid-rows-1">
        {/* Left: the conversation */}
        <section className="min-h-0 border-b lg:border-b-0 lg:border-r">
          <AskPanel matterId={matterId} onSources={onSources} initialQuestion={initial} />
        </section>

        {/* Right: references + the cited passage */}
        <section className="flex min-h-0 flex-col bg-sidebar/40">
          <div className="flex items-center gap-2 border-b px-4 py-3">
            <BookOpen className="size-4 text-primary" aria-hidden />
            <p className="text-sm font-semibold">References</p>
            <span className="text-xs text-muted-foreground">{groups.length ? `${groups.length} source${groups.length === 1 ? "" : "s"} cited` : "none yet"}</span>
            {groups.length > 4 && (
              <label className="ml-auto flex items-center gap-1.5 rounded-lg border bg-background px-2 py-1">
                <Search className="size-3.5 text-muted-foreground" aria-hidden />
                <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter" aria-label="Filter references"
                  className="w-28 bg-transparent text-[13px] outline-none placeholder:text-muted-foreground" />
              </label>
            )}
          </div>

          {groups.length === 0 ? (
            <div className="grid flex-1 place-items-center p-8 text-center">
              <div className="max-w-xs space-y-2">
                <FileText className="mx-auto size-8 text-muted-foreground/50" aria-hidden />
                <p className="text-sm font-medium">Sources will collect here</p>
                <p className="text-[13px] text-muted-foreground">Every note, email and document an answer cites is listed here. Open one to see the exact passage highlighted.</p>
              </div>
            </div>
          ) : (
            <>
              <ul className={`overflow-y-auto p-2 ${current ? "max-h-[38%] shrink-0 border-b" : "flex-1"}`}>
                {shown.map((g) => {
                  const Icon = SOURCE_ICON[g.type] ?? FileText;
                  const on = current?.record_id === g.id;
                  return (
                    <li key={g.id}>
                      <button type="button" onClick={() => open(g.cites, 0)} aria-current={on || undefined}
                        className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors ${on ? "bg-accent" : "hover:bg-accent/50"}`}>
                        <span className={`grid size-8 shrink-0 place-items-center rounded-md ${on ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"}`}><Icon className="size-4" aria-hidden /></span>
                        <span className="min-w-0 flex-1">
                          <span className="block truncate text-[13.5px] font-medium">{g.type === "document" ? shortName(g.title, 48) : g.title}</span>
                          <span className="block truncate text-xs text-muted-foreground">
                            {[TYPE[g.type] ?? g.type, g.date && fmtDate(g.date), g.pages.length && `p. ${[...g.pages].sort((a, b) => a - b).join(", ")}`].filter(Boolean).join(" · ")}
                          </span>
                        </span>
                        <span className="shrink-0 rounded-full border px-2 py-px text-[11px] text-muted-foreground">{g.cites.length} cite{g.cites.length === 1 ? "" : "s"}</span>
                      </button>
                    </li>
                  );
                })}
                {shown.length === 0 && <li className="px-3 py-2 text-[13px] text-muted-foreground">No references match “{filter}”.</li>}
              </ul>
              {current && sel && (
                <div className="relative min-h-0 flex-1 overflow-y-auto p-4 pr-10">
                  <Button variant="ghost" size="icon-sm" className="absolute right-2 top-2" aria-label="Close source" onClick={() => setSel(null)}><X className="size-4" /></Button>
                  <SourceView
                    key={`${sel.i}-${current.record_id}-${current.char_start}`} inline citation={current} pos={sel.i} total={sel.list.length}
                    go={(d) => setSel({ ...sel, i: (sel.i + d + sel.list.length) % sel.list.length })}
                  />
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </SourceTarget>
  );
}

export default function AskPage({ params }: { params: Promise<{ id: string }> }) {
  const matterId = Number(use(params).id);
  return <Suspense><AskWorkspace matterId={matterId} /></Suspense>;
}
