"use client";
import { Calendar, FileText, Mail, Receipt, SquareCheck, StickyNote, Tag, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { chipKey, chipLabel, chipText } from "@/lib/citations";
import { fmtDate } from "@/lib/format";
import type { Citation } from "@/lib/types";
import { useSourceDrawer } from "./SourceDrawer";

export const SOURCE_ICON: Record<string, typeof FileText> = {
  note: StickyNote, communication: Mail, task: SquareCheck, calendar_entry: Calendar, matter_event: Calendar,
  document: FileText, medical_record: FileText, expense: Receipt, time_entry: Receipt, bill: Receipt,
  medical_bill: Receipt, damage: Receipt, custom_field: Tag, contact: User,
};
const MAX_VISIBLE = 2;

export function CitationChip({ citation, siblings }: { citation: Citation; siblings?: Citation[] }) {
  const { open } = useSourceDrawer();
  const list = siblings ?? [citation];
  const Icon = SOURCE_ICON[citation.source_type] ?? FileText;
  return (
    <Popover>
      <PopoverTrigger
        render={<button type="button" className="cite-chip" aria-label={`Source: ${chipText(citation)}`} title={citation.title} />}
      >
        <Icon aria-hidden />{chipText(citation)}
      </PopoverTrigger>
      <PopoverContent className="w-96 text-sm">
        <p className="text-xs text-muted-foreground">
          {citation.source_type.replace(/_/g, " ")} · {citation.title}
          {citation.author && ` · ${citation.author}`}
          {citation.date && ` · ${fmtDate(citation.date)}`}
          {citation.page != null && ` · p.${citation.page}`}
        </p>
        <blockquote className="mt-2 border-l-2 border-primary/60 pl-3 italic leading-relaxed">“{citation.excerpt}”</blockquote>
        <div className="mt-3 flex items-center gap-2">
          <Button size="sm" onClick={() => open(list, Math.max(0, list.indexOf(citation)))}>Open source</Button>
          <span className="ml-auto font-mono text-[10px] text-muted-foreground/70">{chipLabel(citation)}</span>
        </div>
      </PopoverContent>
    </Popover>
  );
}

/** Up to two readable chips (de-duplicated by record+page) and a "+N" popover for the rest. */
export function Chips({ citations }: { citations?: Citation[] | null }) {
  const { open } = useSourceDrawer();
  if (!citations?.length) return null;
  const seen = new Set<string>();
  const unique = citations.filter((c) => (seen.has(chipKey(c)) ? false : (seen.add(chipKey(c)), true)));
  const shown = unique.slice(0, MAX_VISIBLE);
  const rest = unique.slice(MAX_VISIBLE);
  return (
    <span className="ml-1 inline-flex flex-wrap items-center gap-1 align-baseline">
      {shown.map((c, i) => <CitationChip key={i} citation={c} siblings={unique} />)}
      {rest.length > 0 && (
        <Popover>
          <PopoverTrigger render={<button type="button" className="cite-chip" aria-label={`${rest.length} more sources`} />}>+{rest.length}</PopoverTrigger>
          <PopoverContent className="w-72 text-sm">
            <p className="mb-1 text-xs text-muted-foreground">More sources</p>
            <ul className="space-y-1">
              {rest.map((c, i) => (
                <li key={i}>
                  <button type="button" className="text-left hover:underline" onClick={() => open(unique, MAX_VISIBLE + i)}>
                    {chipText(c)} <span className="text-muted-foreground">· {c.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </PopoverContent>
        </Popover>
      )}
    </span>
  );
}
