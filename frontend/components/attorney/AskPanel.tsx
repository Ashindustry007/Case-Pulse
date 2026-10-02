"use client";
import { ArrowUp, MessageSquare, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Chips } from "@/components/citations/CitationChip";
import { useSourceDrawer } from "@/components/citations/SourceDrawer";
import { renderTokens } from "@/components/common/RichText";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { chipKey, chipText } from "@/lib/citations";
import { newState, tokenize } from "@/lib/richtext";
import { segmentIdsInRange, selectionSources } from "@/lib/selection";
import { postSSE } from "@/lib/sse";
import type { AnswerSegment, Citation, LocateResult, SuggestedQuestions } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type Turn = { question: string; segments: AnswerSegment[]; followups: string[]; status?: string; error?: string; done: boolean };
type Pop = { x: number; y: number; text: string; citations: Citation[]; needsVerify: boolean; verify?: LocateResult | "loading" };

// Segment ids restart per answer, so scope them to their turn.
const segKey = (turn: number, id: string): string => `${turn}:${id}`;

const SUGGESTED_SHOWN = 3;

export function AskPanel({ matterId, onClose, onSources, initialQuestion }: {
  matterId: number; onClose?: () => void;
  /** Every citation used so far in the conversation (feeds the Ask page's reference pane). */
  onSources?: (citations: Citation[]) => void;
  /** Asked once on mount (e.g. from the overview's quick-ask box). */
  initialQuestion?: string;
}) {
  const suggested = useApi<SuggestedQuestions>(`/api/matters/${matterId}/suggested-questions`);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [pop, setPop] = useState<Pop | null>(null);
  const [moreIdeas, setMoreIdeas] = useState(false);
  const answersRef = useRef<HTMLDivElement>(null);
  const { open } = useSourceDrawer();
  const busy = turns.some((t) => !t.done);
  const asked = useRef(false);

  useEffect(() => { onSources?.(turns.flatMap((t) => t.segments.flatMap((s) => s.citations ?? []))); }, [turns, onSources]);
  useEffect(() => {
    if (initialQuestion && !asked.current) { asked.current = true; void ask(initialQuestion); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuestion]);

  async function ask(question: string) {
    if (!question.trim() || busy) return;
    setQ("");
    const history = turns.filter((t) => t.done && !t.error).map((t) => ({ question: t.question, answer_text: t.segments.map((s) => s.text).join("") }));
    const idx = turns.length;
    const patch = (fn: (t: Turn) => Turn) => setTurns((ts) => ts.map((t, i) => (i === idx ? fn(t) : t)));
    setTurns((ts) => [...ts, { question, segments: [], followups: [], done: false }]);
    try {
      await postSSE(`/api/matters/${matterId}/ask`, { question, history }, ({ event, data }) => {
        const d = data as Record<string, unknown>;
        if (event === "segment") patch((t) => ({ ...t, status: undefined, segments: [...t.segments, d as unknown as AnswerSegment] }));
        else if (event === "status") patch((t) => ({ ...t, status: String(d.message ?? "") }));
        else if (event === "done") patch((t) => ({ ...t, done: true, status: undefined, followups: (d.followups as string[]) ?? [] }));
        else if (event === "error") patch((t) => ({ ...t, done: true, error: String(d.message ?? "Something went wrong") }));
      });
      patch((t) => (t.done ? t : { ...t, done: true }));
    } catch (e) {
      patch((t) => ({ ...t, done: true, error: String(e) }));
    }
  }

  function onMouseUp() {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !answersRef.current) { setPop(null); return; }
    const range = sel.getRangeAt(0);
    const ids = segmentIdsInRange(answersRef.current, range);
    if (!ids.length) { setPop(null); return; }
    const all = turns.flatMap((t, i) => t.segments.map((s) => ({ ...s, id: segKey(i, s.id) })));
    const { citations, needsVerify } = selectionSources(all, ids);
    const rect = range.getBoundingClientRect();
    setPop({ x: rect.left, y: rect.bottom + 6, text: sel.toString().trim(), citations, needsVerify });
  }

  async function verify() {
    if (!pop) return;
    setPop({ ...pop, verify: "loading" });
    try {
      const r = await api<LocateResult>(`/api/matters/${matterId}/locate`, { json: { text: pop.text } });
      setPop((p) => p && { ...p, verify: r });
    } catch {
      setPop((p) => p && { ...p, verify: { supported: false, citations: [], explanation: "Verification failed." } });
    }
  }

  const ideas = suggested.data?.questions ?? [];
  const shownIdeas = moreIdeas ? ideas : ideas.slice(0, SUGGESTED_SHOWN);

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col">
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <MessageSquare className="size-4 text-primary" aria-hidden />
        <p className="text-sm font-semibold">Ask the case</p>
        <span className="text-xs text-muted-foreground">answers are cited</span>
        {onClose && <Button variant="ghost" size="icon-sm" className="ml-auto" aria-label="Close Ask panel" onClick={onClose}><X className="size-4" /></Button>}
      </div>

      <div ref={answersRef} onMouseUp={onMouseUp} className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4 text-[14px]">
        {turns.length === 0 && (
          <div className="space-y-4">
            <p className="flex items-start gap-2 text-[13px] leading-relaxed text-muted-foreground">
              <Sparkles className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
              Ask anything about this case. Highlight any part of an answer to see exactly where it came from.
            </p>
            <div className="space-y-2">
              {shownIdeas.map((q0) => (
                <button key={q0} type="button" onClick={() => ask(q0)} disabled={busy}
                  className="block w-full min-w-0 rounded-lg border bg-card px-3 py-2 text-left text-[13px] leading-snug transition-colors hover:border-primary/50 hover:bg-accent/40 disabled:opacity-50">
                  <span className="line-clamp-2">{q0}</span>
                </button>
              ))}
              {ideas.length > SUGGESTED_SHOWN && (
                <button type="button" className="text-xs text-primary hover:underline" onClick={() => setMoreIdeas((v) => !v)}>
                  {moreIdeas ? "Fewer ideas" : `${ideas.length - SUGGESTED_SHOWN} more ideas`}
                </button>
              )}
            </div>
          </div>
        )}

        {turns.map((t, i) => {
          const st = newState();   // bold/bullet state carries across the answer's segments
          let prevSig = "";
          return (
            <div key={i} className="space-y-2.5">
              <p className="ml-auto w-fit max-w-[88%] rounded-2xl rounded-br-sm bg-accent px-3.5 py-2 text-[13.5px]">{t.question}</p>
              <div className="min-w-0 leading-relaxed [overflow-wrap:anywhere]">
                {t.segments.map((s) => {
                  const sig = (s.citations ?? []).map(chipKey).join(",");
                  const showChips = !!sig && sig !== prevSig;   // don't repeat identical chips on consecutive fragments
                  prevSig = sig || prevSig;
                  return (
                    <span key={s.id} data-seg={segKey(i, s.id)}>
                      {renderTokens(tokenize(s.text, st), s.id)}
                      {showChips && <Chips citations={s.citations} />}
                    </span>
                  );
                })}
                {!t.done && <span className="animate-pulse text-muted-foreground"> {t.status ?? "…"}</span>}
              </div>
              {t.error && <p className="text-danger">⚠ {t.error}</p>}
              {t.done && t.followups.length > 0 && (
                <div className="flex flex-col items-start gap-1 pt-1">
                  {t.followups.map((f) => <button key={f} type="button" className="text-left text-[13px] text-muted-foreground hover:text-primary" onClick={() => ask(f)}>↳ {f}</button>)}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {pop && (
        <div className="fixed z-50 w-80 rounded-xl border bg-popover p-3 text-sm shadow-2xl" style={{ left: Math.min(pop.x, window.innerWidth - 340), top: pop.y }}>
          <p className="section-label mb-1.5">Sources for your selection</p>
          <ul className="space-y-1">
            {pop.citations.map((c, i) => (
              <li key={i}><button className="text-left text-[13px] hover:text-primary" onClick={() => open(pop.citations, i)}><span className="font-medium">{chipText(c)}</span> <span className="text-muted-foreground">· {c.title}</span> ▸</button></li>
            ))}
            {pop.citations.length === 0 && <li className="text-[13px] text-muted-foreground">This text isn&apos;t linked to a source.</li>}
          </ul>
          {pop.needsVerify && !pop.verify && <Button size="sm" variant="outline" className="mt-2" onClick={verify}>Verify selection</Button>}
          {pop.verify === "loading" && <p className="mt-2 text-muted-foreground">Checking the case file…</p>}
          {pop.verify && pop.verify !== "loading" && (pop.verify.supported && pop.verify.citations.length ? (
            <ul className="mt-2 space-y-1 border-t pt-2">
              {pop.verify.citations.map((c, i) => (
                <li key={i}><button className="text-left text-[13px] hover:text-primary" onClick={() => open((pop.verify as LocateResult).citations, i)}>✔ <span className="font-medium">{chipText(c)}</span> <span className="text-muted-foreground">· {c.excerpt.slice(0, 80)}…</span> ▸</button></li>
              ))}
            </ul>
          ) : <p className="mt-2 text-muted-foreground">No supporting source found in the case file.</p>)}
        </div>
      )}

      <form className="border-t p-3" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
        <div className="flex items-center gap-2 rounded-xl border bg-card py-1 pl-3 pr-1 focus-within:border-ring">
          <input
            value={q} onChange={(e) => setQ(e.target.value)} disabled={busy} placeholder="Ask anything about this case…" aria-label="Your question"
            className="h-8 min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-muted-foreground disabled:opacity-60"
          />
          <Button type="submit" size="icon" className="rounded-lg" disabled={busy || !q.trim()} aria-label="Send"><ArrowUp className="size-4" /></Button>
        </div>
      </form>
    </div>
  );
}
