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
