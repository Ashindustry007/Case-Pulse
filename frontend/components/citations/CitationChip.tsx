"use client";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { chipLabel } from "@/lib/citations";
import { fmtDate } from "@/lib/format";
import type { Citation } from "@/lib/types";
import { useSourceDrawer } from "./SourceDrawer";

export function CitationChip({ citation, siblings }: { citation: Citation; siblings?: Citation[] }) {
  const { open } = useSourceDrawer();
  const list = siblings ?? [citation];
  return (
    <Popover>
      <PopoverTrigger
        render={<button type="button" className="cite-chip" aria-label={`Source ${chipLabel(citation)}`} />}
      >
        [{chipLabel(citation)}]
      </PopoverTrigger>
      <PopoverContent className="w-96 text-sm">
        <p className="text-xs text-muted-foreground">
          {citation.source_type.replace(/_/g, " ")} · {citation.title}
          {citation.author && ` · ${citation.author}`}
          {citation.date && ` · ${fmtDate(citation.date)}`}
          {citation.page != null && ` · p.${citation.page}`}
        </p>
        <blockquote className="mt-2 border-l-2 pl-3 italic">“{citation.excerpt}”</blockquote>
        <Button size="sm" className="mt-3" onClick={() => open(list, Math.max(0, list.indexOf(citation)))}>Open source</Button>
      </PopoverContent>
    </Popover>
  );
}

export function Chips({ citations }: { citations?: Citation[] | null }) {
  if (!citations?.length) return null;
  return (
    <span className="ml-1 inline-flex flex-wrap gap-0.5 align-baseline">
      {citations.map((c, i) => <CitationChip key={i} citation={c} siblings={citations} />)}
    </span>
  );
}
