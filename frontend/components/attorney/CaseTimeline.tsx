"use client";
import { CalendarDays, ChevronLeft, ChevronRight, FileText, Hourglass, List, Search, Star } from "lucide-react";
import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { Chips, SOURCE_ICON } from "@/components/citations/CitationChip";
import { Panel } from "@/components/common/Section";
import { Loading } from "@/components/common/states";
import { parseISODate } from "@/lib/format";
import type { Brief, Citation, DeadlineItem, Deadlines, Timeline } from "@/lib/types";

type Status = "overdue" | "upcoming" | "waiting";
export type CaseEvent = {
  id: string; iso: string | null; date: Date | null; type: string; title: string; detail?: string | null;
  author?: string | null; importance?: number | null; citations: Citation[];
  status?: Status; waitingOn?: string | null; assignee?: string | null; key?: boolean;
};

const TYPE_LABEL: Record<string, string> = {
  note: "Note", communication: "Email", task: "Task", calendar_entry: "Calendar", document: "Document", expense: "Expense",
  custom_field: "Case field", deadline: "Deadline", time_entry: "Time", bill: "Bill", medical_record: "Medical record",
  medical_bill: "Medical bill", damage: "Damages", matter_event: "Event", contact: "Contact",
};
const STATUS_LABEL: Record<Status, string> = { overdue: "Overdue", upcoming: "Upcoming", waiting: "Waiting on" };
const STATUS_TONE: Record<Status, string> = {
  overdue: "border-danger/40 bg-danger/10 text-danger", upcoming: "border-warning/40 bg-warning/10 text-warning",
  waiting: "border-border bg-muted text-muted-foreground",
};

const dayKey = (d: Date) => `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
const monthKey = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
const monthLabel = (d: Date) => d.toLocaleDateString("en-US", { month: "long", year: "numeric" });

/** One event per record: timeline records, with deadlines (tasks, calendar, SOL, waiting-on) moved to their due date. */
export function buildEvents(timeline: Timeline, deadlines: Deadlines | undefined, brief: Brief | undefined): CaseEvent[] {
  const keyIds = new Set((brief?.key_moments ?? []).flatMap((k) => k.citations.map((c) => c.record_id)));
  const map = new Map<string, CaseEvent>();
  for (const t of timeline.items) {
    map.set(t.record_id, {
      id: t.record_id, iso: t.occurred_at ?? null, date: null, type: t.type, title: t.title,
      detail: t.one_liner && t.one_liner !== t.title ? t.one_liner : null, author: t.author, importance: t.importance,
      citations: t.citations, key: keyIds.has(t.record_id),
    });
  }
  const merge = (d: DeadlineItem, status: Status) => {
    const rid = d.id.replace(/^waiting:/, "");
    const ex = map.get(rid);
    if (ex) {
      if (d.due_at) ex.iso = d.due_at;
      if (!ex.status || ex.status === "waiting") ex.status = status;
      ex.waitingOn = d.waiting_on ?? ex.waitingOn;
      ex.assignee = d.assignee ?? ex.assignee;
    } else {
      map.set(rid, {
        id: rid, iso: d.due_at ?? null, date: null, title: d.title, citations: d.citations, status,
        type: d.kind === "calendar" ? "calendar_entry" : d.kind === "sol" ? "deadline" : "task",
        waitingOn: d.waiting_on, assignee: d.assignee, key: keyIds.has(rid),
      });
    }
  };
  deadlines?.waiting_on.forEach((d) => merge(d, "waiting"));
  deadlines?.upcoming.forEach((d) => merge(d, "upcoming"));
  deadlines?.overdue.forEach((d) => merge(d, "overdue"));
  const out = [...map.values()].map((e) => ({ ...e, date: e.iso ? parseISODate(e.iso) : null }));
  return out.sort((a, b) => (b.date?.getTime() ?? -Infinity) - (a.date?.getTime() ?? -Infinity));
}

const FILTERS: [string, string, (e: CaseEvent) => boolean][] = [
  ["all", "All", () => true],
  ["key", "Key moments", (e) => !!e.key],
  ["due", "Deadlines", (e) => !!e.status],
  ["communication", "Emails", (e) => e.type === "communication"],
  ["note", "Notes", (e) => e.type === "note"],
  ["document", "Documents", (e) => e.type === "document"],
  ["calendar_entry", "Calendar", (e) => e.type === "calendar_entry"],
  ["task", "Tasks", (e) => e.type === "task"],
  ["expense", "Expenses", (e) => e.type === "expense"],
  ["custom_field", "Case fields", (e) => e.type === "custom_field"],
];

export function CaseTimeline({ timeline, deadlines, brief, aside }: {
  timeline?: Timeline; deadlines?: Deadlines; brief?: Brief; aside?: React.ReactNode;
}) {
  const [view, setView] = useState<"list" | "calendar">("list");
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [day, setDay] = useState<Date | null>(null);
  const events = useMemo(() => (timeline ? buildEvents(timeline, deadlines, brief) : []), [timeline, deadlines, brief]);
  if (!timeline) return <Loading lines={12} />;

  const pred = FILTERS.find((f) => f[0] === filter)?.[2] ?? (() => true);
  const needle = q.trim().toLowerCase();
  const shown = events.filter((e) => pred(e) && (!needle || `${e.title} ${e.detail ?? ""} ${e.author ?? ""}`.toLowerCase().includes(needle)));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div role="tablist" aria-label="View" className="inline-flex rounded-lg bg-muted p-0.5 text-[13px]">
          {([["list", "List", List], ["calendar", "Calendar", CalendarDays]] as const).map(([k, label, Icon]) => (
            <button key={k} role="tab" type="button" aria-selected={view === k} onClick={() => setView(k)}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1 transition-colors ${view === k ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground"}`}>
              <Icon className="size-3.5" aria-hidden /> {label}
            </button>
          ))}
        </div>
        <label className="ml-auto flex items-center gap-1.5 rounded-lg border bg-card px-2.5 py-1.5">
          <Search className="size-3.5 text-muted-foreground" aria-hidden />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search events" aria-label="Search events"
            className="w-44 bg-transparent text-[13px] outline-none placeholder:text-muted-foreground" />
        </label>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map(([k, label, f]) => {
          const n = events.filter(f).length;
          if (!n && k !== "all") return null;
          return (
            <button key={k} type="button" onClick={() => setFilter(k)} aria-pressed={filter === k}
              className={`rounded-full border px-2.5 py-0.5 text-[12.5px] transition-colors ${filter === k ? "border-primary/50 bg-primary/12 text-primary" : "text-muted-foreground hover:text-foreground"}`}>
              {label} <span className="opacity-70">{n}</span>
            </button>
          );
        })}
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        {view === "list" ? <EventList events={shown} /> : <CalendarView events={shown} day={day} onDay={setDay} />}
        <div className="space-y-6 xl:sticky xl:top-4">
          {view === "calendar" && <DayPanel day={day} events={shown} />}
          {aside}
        </div>
      </div>
    </div>
  );
}

function EventRow({ e }: { e: CaseEvent }) {
  const Icon = e.type === "deadline" ? Hourglass : SOURCE_ICON[e.type] ?? FileText;
  return (
    <li className="grid grid-cols-[3.25rem_auto_1fr] items-start gap-3 px-4 py-2.5">
      <div className="text-center leading-tight">
        {e.date ? (
          <>
            <p className="text-[15px] font-semibold">{e.date.getDate()}</p>
            <p className="text-[10.5px] uppercase tracking-wider text-muted-foreground">{e.date.toLocaleDateString("en-US", { weekday: "short" })}</p>
          </>
        ) : <p className="text-xs text-muted-foreground">—</p>}
      </div>
      <span className={`mt-0.5 grid size-7 place-items-center rounded-md ${e.status === "overdue" ? "bg-danger/12 text-danger" : e.key ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground"}`}>
        <Icon className="size-3.5" aria-hidden />
      </span>
      <div className="min-w-0">
        <p className="text-[13.5px] leading-snug">
          <span className="font-medium">{e.title}</span>
          {e.key && <Star className="ml-1.5 inline size-3 fill-primary text-primary" aria-label="Key moment" />}
          {e.status && <span className={`ml-2 rounded-full border px-1.5 py-px text-[10px] font-medium uppercase tracking-wider ${STATUS_TONE[e.status]}`}>{STATUS_LABEL[e.status]}</span>}
          <Chips citations={e.citations} />
        </p>
        {e.detail && <p className="mt-0.5 line-clamp-2 text-[13px] text-muted-foreground">{e.detail}</p>}
        <p className="mt-0.5 text-xs text-muted-foreground">
          {[TYPE_LABEL[e.type] ?? e.type, e.author && `by ${e.author}`, e.waitingOn && `waiting on ${e.waitingOn}`, e.assignee && `assigned ${e.assignee}`].filter(Boolean).join(" · ")}
        </p>
      </div>
    </li>
  );
}

/** Month-grouped list, newest first, with a "Today" divider between what's coming and what happened. */
function EventList({ events }: { events: CaseEvent[] }) {
  const now = new Date();
  const groups: { key: string; label: string; items: CaseEvent[] }[] = [];
  for (const e of events) {
    const key = e.date ? monthKey(e.date) : "undated";
    let g = groups[groups.length - 1];
    if (!g || g.key !== key) groups.push((g = { key, label: e.date ? monthLabel(e.date) : "Undated", items: [] }));
    g.items.push(e);
  }
  // The "Today" divider sits above the newest event that is not in the future.
  const firstPast = events.find((e) => e.date && e.date <= now)?.id;
  if (!events.length) return <Panel><p className="text-muted-foreground">No events match.</p></Panel>;
  return (
    <div className="space-y-5">
      {groups.map((g) => (
        <section key={g.key}>
          <h3 className="sticky top-0 z-10 -mx-1 mb-2 bg-background/90 px-1 py-1 text-[13px] font-semibold backdrop-blur">
            {g.label} <span className="font-normal text-muted-foreground">· {g.items.length}</span>
          </h3>
          <Panel className="p-0">
            <ol className="divide-y">
              {g.items.map((e) => (
                <Fragment key={e.id}>
                  {e.id === firstPast && (
                    <li className="flex items-center gap-2 bg-primary/8 px-4 py-1 text-[11px] font-semibold uppercase tracking-wider text-primary">
                      <span className="size-1.5 rounded-full bg-primary" /> Today · {now.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </li>
                  )}
                  <EventRow e={e} />
                </Fragment>
              ))}
            </ol>
          </Panel>
        </section>
      ))}
    </div>
  );
}

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const pillTone = (e: CaseEvent) =>
  e.status === "overdue" ? "bg-danger/15 text-danger" : e.status === "upcoming" ? "bg-warning/15 text-warning"
    : e.key ? "bg-primary/15 text-primary" : "bg-muted text-foreground/80";

/** Scrollable stack of month grids, oldest at the top; opens on the current month. */
function CalendarView({ events, day, onDay }: { events: CaseEvent[]; day: Date | null; onDay: (d: Date) => void }) {
  const scroller = useRef<HTMLDivElement>(null);
  const byDay = useMemo(() => {
    const m = new Map<string, CaseEvent[]>();
    for (const e of events) if (e.date) m.set(dayKey(e.date), [...(m.get(dayKey(e.date)) ?? []), e]);
    return m;
  }, [events]);
  const months = useMemo(() => {
    const dated = events.filter((e) => e.date).map((e) => e.date!.getTime());
    const today = new Date();
    if (!dated.length) return [new Date(today.getFullYear(), today.getMonth(), 1)];
    const lo = new Date(Math.min(...dated, today.getTime())), hi = new Date(Math.max(...dated, today.getTime()));
    const out: Date[] = [];
    for (let d = new Date(lo.getFullYear(), lo.getMonth(), 1); d <= hi; d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) out.push(d);
    return out;
  }, [events]);
  const todayKey = dayKey(new Date());
  const thisMonth = monthKey(new Date());

  // Scroll only the calendar box (scrollIntoView would also move the page). Sections are offset from the scroller,
  // minus the sticky weekday header.
  const scrollTo = (sec: HTMLElement | null | undefined, smooth = true) => {
    const el = scroller.current;
    if (!el || !sec) return;
    const head = el.firstElementChild instanceof HTMLElement ? el.firstElementChild.offsetHeight : 0;
    el.scrollTo({ top: sec.offsetTop - head, behavior: smooth ? "smooth" : "auto" });
  };
  const monthEl = (k: string) => scroller.current?.querySelector<HTMLElement>(`[data-month="${k}"]`);

  useEffect(() => { scrollTo(monthEl(thisMonth), false); }, [thisMonth]);

  const jump = (dir: number) => {
    const el = scroller.current;
    if (!el) return;
    const sections = [...el.querySelectorAll<HTMLElement>("[data-month]")];
    const head = el.firstElementChild instanceof HTMLElement ? el.firstElementChild.offsetHeight : 0;
    const idx = sections.findIndex((s) => s.offsetTop - head >= el.scrollTop - 4);
    scrollTo(sections[Math.max(0, Math.min(sections.length - 1, (idx < 0 ? sections.length - 1 : idx) + dir))]);
  };

  return (
    <Panel className="p-0">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <button type="button" onClick={() => jump(-1)} className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground" aria-label="Previous month"><ChevronLeft className="size-4" /></button>
        <button type="button" onClick={() => jump(1)} className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-foreground" aria-label="Next month"><ChevronRight className="size-4" /></button>
        <button type="button" onClick={() => scrollTo(monthEl(thisMonth))}
          className="rounded-md border px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground">Today</button>
        <span className="ml-auto flex items-center gap-3 text-[11px] text-muted-foreground">
          <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-danger" />Overdue</span>
          <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-warning" />Upcoming</span>
          <span className="flex items-center gap-1"><span className="size-2 rounded-full bg-primary" />Key</span>
        </span>
      </div>
      <div ref={scroller} className="relative max-h-[calc(100dvh-15rem)] min-h-[420px] overflow-y-auto">
        <div className="sticky top-0 z-10 grid grid-cols-7 border-b bg-card text-center text-[11px] uppercase tracking-wider text-muted-foreground">
          {WEEKDAYS.map((w) => <span key={w} className="py-1.5">{w}</span>)}
        </div>
        {months.map((m) => {
          const first = m.getDay();
          const days = new Date(m.getFullYear(), m.getMonth() + 1, 0).getDate();
          return (
            <section key={monthKey(m)} data-month={monthKey(m)} className="border-b last:border-b-0">
              <h3 className="px-3 pb-1 pt-3 text-[13px] font-semibold">{monthLabel(m)}</h3>
              <div className="grid grid-cols-7 gap-px px-1 pb-2">
                {Array.from({ length: first }, (_, i) => <span key={`b${i}`} />)}
                {Array.from({ length: days }, (_, i) => {
                  const d = new Date(m.getFullYear(), m.getMonth(), i + 1);
                  const k = dayKey(d);
                  const list = byDay.get(k) ?? [];
                  const selected = day && dayKey(day) === k;
                  return (
                    <button key={k} type="button" onClick={() => onDay(d)}
                      className={`flex min-h-[78px] min-w-0 flex-col gap-0.5 rounded-md p-1 text-left transition-colors ${selected ? "bg-accent ring-1 ring-primary/50" : list.length ? "hover:bg-accent/60" : "hover:bg-accent/30"}`}>
                      <span className={`grid size-5 place-items-center rounded-full text-[11px] ${k === todayKey ? "bg-primary font-semibold text-primary-foreground" : list.length ? "text-foreground" : "text-muted-foreground/60"}`}>{i + 1}</span>
                      {list.slice(0, 2).map((e) => (
                        <span key={e.id} className={`truncate rounded px-1 py-px text-[10.5px] leading-tight ${pillTone(e)}`}>{e.title}</span>
                      ))}
                      {list.length > 2 && <span className="px-1 text-[10.5px] text-muted-foreground">+{list.length - 2} more</span>}
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
      </div>
    </Panel>
  );
}

function DayPanel({ day, events }: { day: Date | null; events: CaseEvent[] }) {
  const list = day ? events.filter((e) => e.date && dayKey(e.date) === dayKey(day)) : [];
  return (
    <section className="space-y-2">
      <h2 className="section-label">{day ? day.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" }) : "Pick a day"}</h2>
      <Panel className="p-0">
        {!day ? <p className="p-4 text-[13px] text-muted-foreground">Click any day in the calendar to see everything that happened or is due.</p>
          : list.length === 0 ? <p className="p-4 text-[13px] text-muted-foreground">Nothing on this day.</p>
            : <ol className="max-h-[60vh] divide-y overflow-y-auto">{list.map((e) => <EventRow key={e.id} e={e} />)}</ol>}
      </Panel>
    </section>
  );
}
