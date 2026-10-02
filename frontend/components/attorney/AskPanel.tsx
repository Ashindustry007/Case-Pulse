"use client";
import { Send } from "lucide-react";
import { useRef, useState } from "react";
import { CitationChip } from "@/components/citations/CitationChip";
import { useSourceDrawer } from "@/components/citations/SourceDrawer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { chipLabel } from "@/lib/citations";
import { segmentIdsInRange, selectionSources } from "@/lib/selection";
import { postSSE } from "@/lib/sse";
import type { AnswerSegment, Citation, LocateResult, SuggestedQuestions } from "@/lib/types";
import { useApi } from "@/lib/use-api";

type Turn = { question: string; segments: AnswerSegment[]; followups: string[]; status?: string; error?: string; done: boolean };
type Pop = { x: number; y: number; text: string; citations: Citation[]; needsVerify: boolean; verify?: LocateResult | "loading" };

// Segment ids restart per answer, so scope them to their turn.
const segKey = (turn: number, id: string): string => `${turn}:${id}`;

export function AskPanel({ matterId }: { matterId: number }) {
  const suggested = useApi<SuggestedQuestions>(`/api/matters/${matterId}/suggested-questions`);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [q, setQ] = useState("");
  const [pop, setPop] = useState<Pop | null>(null);
  const answersRef = useRef<HTMLDivElement>(null);
  const { open } = useSourceDrawer();
  const busy = turns.some((t) => !t.done);

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

  return (
    <div className="flex h-full flex-col">
      <div className="border-b p-3">
        <p className="text-sm font-semibold">💬 Ask the case</p>
        <div className="mt-2 flex flex-wrap gap-1">
          {suggested.data?.questions.map((s) => <Button key={s} variant="outline" size="sm" className="h-auto py-1 text-xs" onClick={() => ask(s)}>{s}</Button>)}
        </div>
      </div>
      <div ref={answersRef} onMouseUp={onMouseUp} className="flex-1 space-y-4 overflow-y-auto p-3 text-sm">
        {turns.map((t, i) => (
          <div key={i} className="space-y-1">
            <p className="font-medium">Q: {t.question}</p>
            <p className="leading-relaxed">
              {t.segments.map((s) => (
                <span key={s.id} data-seg={segKey(i, s.id)}>
                  {s.text}
                  {s.citations?.map((c, j) => <sup key={j}><CitationChip citation={c} siblings={s.citations} /></sup>)}
                </span>
              ))}
              {!t.done && <span className="animate-pulse text-muted-foreground"> {t.status ?? "…"}</span>}
            </p>
            {t.error && <p className="text-destructive">⚠ {t.error}</p>}
            {t.followups.length > 0 && (
              <div className="flex flex-wrap gap-1">{t.followups.map((f) => <Button key={f} variant="ghost" size="sm" className="h-auto py-0.5 text-xs" onClick={() => ask(f)}>↳ {f}</Button>)}</div>
            )}
          </div>
        ))}
      </div>
      {pop && (
        <div className="fixed z-50 w-80 rounded-md border bg-popover p-3 text-sm shadow-md" style={{ left: Math.min(pop.x, window.innerWidth - 340), top: pop.y }}>
          <p className="mb-1 text-xs font-medium text-muted-foreground">Sources for selection</p>
          <ul className="space-y-1">
            {pop.citations.map((c, i) => (
              <li key={i}><button className="text-left hover:underline" onClick={() => open(pop.citations, i)}>[{chipLabel(c)}] {c.title}{c.page != null && ` p.${c.page}`} ▸</button></li>
            ))}
          </ul>
          {pop.needsVerify && !pop.verify && <Button size="sm" variant="outline" className="mt-2" onClick={verify}>Verify selection</Button>}
          {pop.verify === "loading" && <p className="mt-2 text-muted-foreground">Checking the case file…</p>}
          {pop.verify && pop.verify !== "loading" && (pop.verify.supported && pop.verify.citations.length ? (
            <ul className="mt-2 space-y-1 border-t pt-2">
              {pop.verify.citations.map((c, i) => (
                <li key={i}><button className="text-left hover:underline" onClick={() => open((pop.verify as LocateResult).citations, i)}>✔ [{chipLabel(c)}] {c.excerpt.slice(0, 80)}… ▸</button></li>
              ))}
            </ul>
          ) : <p className="mt-2 text-muted-foreground">No supporting source found in the case file.</p>)}
        </div>
      )}
      <form className="flex gap-2 border-t p-3" onSubmit={(e) => { e.preventDefault(); ask(q); }}>
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask anything about this case…" disabled={busy} />
        <Button type="submit" size="icon" disabled={busy || !q.trim()}><Send className="h-4 w-4" /></Button>
      </form>
    </div>
  );
}
