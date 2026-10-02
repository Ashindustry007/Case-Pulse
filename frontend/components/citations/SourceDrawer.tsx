"use client";
import { ChevronLeft, ChevronRight, ExternalLink, FileText } from "lucide-react";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { ErrorNote, Loading } from "@/components/common/states";
import { Button, buttonVariants } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { apiUrl } from "@/lib/api";
import { locateSpan } from "@/lib/citations";
import { fmtDate } from "@/lib/format";
import type { Citation, DocumentPage, SourceRecord } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type Ctx = { open: (list: Citation[], index?: number) => void };
const SourceCtx = createContext<Ctx>({ open: () => {} });
export const useSourceDrawer = () => useContext(SourceCtx);

export function SourceDrawerProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<{ list: Citation[]; i: number } | null>(null);
  const cite = state?.list[state.i];
  return (
    <SourceCtx.Provider value={{ open: (list, i = 0) => setState({ list, i }) }}>
      {children}
      <Sheet open={!!state} onOpenChange={(o) => !o && setState(null)}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-3xl">
          {state && cite && (
            <SourceView
              key={`${state.i}-${cite.record_id}`}
              citation={cite}
              pos={state.i}
              total={state.list.length}
              go={(d) => setState({ ...state, i: (state.i + d + state.list.length) % state.list.length })}
            />
          )}
        </SheetContent>
      </Sheet>
    </SourceCtx.Provider>
  );
}

function SourceView({ citation, pos, total, go }: { citation: Citation; pos: number; total: number; go: (d: number) => void }) {
  const isPage = citation.page != null;
  const id = encodeURIComponent(citation.record_id);
  const record = useApi<SourceRecord>(`/api/records/${id}`);
  const page = useApi<DocumentPage>(isPage ? `/api/documents/${id}/pages/${citation.page}` : null);
  const markRef = useRef<HTMLElement>(null);
  const text = isPage ? page.data?.text : record.data?.body_text;
  useEffect(() => { markRef.current?.scrollIntoView({ block: "center" }); }, [text]);
  const [before, mark, after] = locateSpan(text ?? "", citation);
  const clioUrl = citation.clio_url ?? record.data?.clio_url;
  const r = record.data;

  return (
    <div className="space-y-3">
      <SheetHeader>
        <SheetTitle className="flex items-center gap-2 text-base">
          <FileText className="size-4 shrink-0 text-primary" /> {citation.title}
          {isPage && ` · page ${citation.page}${page.data ? `/${page.data.page_count}` : ""}`}
        </SheetTitle>
        <p className="text-xs text-muted-foreground">
          {citation.source_type.replace(/_/g, " ")}
          {(citation.date ?? r?.occurred_at) && ` · ${fmtDate(citation.date ?? r?.occurred_at)}`}
          {(citation.author ?? r?.author) && ` · by ${citation.author ?? r?.author}`}
        </p>
      </SheetHeader>
      <div className="flex items-center gap-2">
        {total > 1 && (
          <>
            <Button variant="outline" size="sm" onClick={() => go(-1)}><ChevronLeft className="h-4 w-4" /> prev cite</Button>
            <span className="text-xs text-muted-foreground">{pos + 1} / {total}</span>
            <Button variant="outline" size="sm" onClick={() => go(1)}>next cite <ChevronRight className="h-4 w-4" /></Button>
          </>
        )}
        {clioUrl && (
          <a href={clioUrl} target="_blank" rel="noreferrer" className={buttonVariants({ variant: "link", size: "sm", className: "ml-auto" })}>
            Open in Clio <ExternalLink className="ml-1 h-3 w-3" />
          </a>
        )}
      </div>
      <ErrorNote error={isPage ? page.error : record.error} />
      {text == null ? <Loading lines={8} /> : (
        <div className={isPage && page.data?.image_url ? "grid grid-cols-2 gap-3" : ""}>
          {isPage && page.data?.image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={apiUrl(page.data.image_url)} alt={`Page ${citation.page}`} className="w-full rounded-lg border" />
          )}
          <pre className="whitespace-pre-wrap rounded-lg border bg-muted/30 p-4 font-sans text-[13.5px] leading-relaxed">
            {before}<mark ref={markRef} className="cite-span">{mark}</mark>{after}
          </pre>
        </div>
      )}
    </div>
  );
}
