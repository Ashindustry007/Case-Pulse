import { parseISODate } from "./format";
import type { Citation } from "./types";

type CiteLike = Pick<Citation, "record_id" | "source_type" | "char_start" | "char_end" | "excerpt"> & { page?: number | null };

const PREFIX: Record<string, string> = {
  note: "n", communication: "c", task: "t", calendar_entry: "cal", document: "d", expense: "x", time_entry: "te",
  bill: "b", medical_record: "mr", medical_bill: "mb", damage: "dm", custom_field: "cf", matter_event: "ev", contact: "ct",
};

export function chipLabel(c: Pick<CiteLike, "record_id" | "source_type" | "page">): string {
  const id = c.record_id.includes(":") ? c.record_id.slice(c.record_id.indexOf(":") + 1) : c.record_id;
  const base = `${PREFIX[c.source_type] ?? "s"}${id}`;
  return c.page != null ? `${base} p${c.page}` : base;
}

/** [before, cited, after]. Uses offsets; if they don't match the excerpt, searches for the excerpt instead. */
export function locateSpan(text: string, c: CiteLike): [string, string, string] {
  let s = Math.max(0, Math.min(c.char_start, text.length));
  let e = Math.max(s, Math.min(c.char_end, text.length));
  if (text.slice(s, e) !== c.excerpt) {
    const found = text.indexOf(c.excerpt);
    if (found >= 0) { s = found; e = found + c.excerpt.length; }
  }
  return [text.slice(0, s), text.slice(s, e), text.slice(e)];
}

export function uniqueCitations<T extends CiteLike>(list: T[]): T[] {
  const seen = new Set<string>();
  return list.filter((c) => {
    const k = `${c.record_id}|${c.page ?? ""}|${c.char_start}|${c.char_end}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

const TYPE_LABEL: Record<string, string> = {
  note: "Note", communication: "Email", task: "Task", calendar_entry: "Event", document: "Doc", expense: "Expense",
  time_entry: "Time", bill: "Bill", medical_record: "Records", medical_bill: "Bill", damage: "Damages",
  custom_field: "Field", matter_event: "Event", contact: "Contact",
};

/** Short, human chip text — never a raw record id: "Note · Sep 9", "Doc p3", "Field · Policy Limits". */
/** "04-medical-records__created__acme-ortho-records-2023.pdf" → "acme ortho records 2023" (readable, cut to `max`). */
export function shortName(title: string, max = 20): string {
  const last = title.split("__").pop() ?? title;
  const words = last.replace(/\.[A-Za-z0-9]{2,4}$/, "").replace(/[-_\s]+/g, " ").replace(/^\d+\s+/, "").trim();
  return words.length > max ? `${words.slice(0, max - 1).trimEnd()}…` : words;
}

export function chipText(c: Pick<Citation, "source_type" | "title" | "date"> & { page?: number | null }): string {
  const base = TYPE_LABEL[c.source_type] ?? "Source";
  if (c.page != null) {
    const name = c.source_type === "document" ? shortName(c.title) : "";
    return name ? `${name} · p${c.page}` : `${base} p${c.page}`;
  }
  if (c.source_type === "custom_field") {
    const name = c.title.split("·").pop()?.trim();
    return name ? `${base} · ${name}` : base;
  }
  if (c.date) {
    const d = parseISODate(c.date);
    if (!Number.isNaN(d.getTime())) return `${base} · ${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
  }
  return base;
}

/** What a chip stands for, for de-duplicating the visible chips (full list stays available to the drawer). */
export const chipKey = (c: Pick<Citation, "record_id"> & { page?: number | null }): string => `${c.record_id}|${c.page ?? ""}`;
