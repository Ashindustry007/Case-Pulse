/** Case stage as a compact dot stepper: done = filled gold, current = ringed gold + label, future = dim. */
export function StageStepper({ stages, index, current }: { stages: string[]; index: number | null; current: string | null }) {
  if (!stages.length) return current ? <span className="text-sm">{current}</span> : null;
  return (
    <div className="flex flex-col items-end gap-1.5">
      <ol className="flex items-center gap-1" aria-label="Case stage">
        {stages.map((s, i) => {
          const done = index != null && i < index;
          const now = index === i;
          return (
            <li key={s} title={s} className="flex items-center gap-1">
              <span className={`block rounded-full transition-colors ${now ? "size-3 bg-primary ring-4 ring-primary/20" : done ? "size-2 bg-primary/70" : "size-2 bg-muted-foreground/30"}`} />
              {i < stages.length - 1 && <span className={`block h-px w-4 ${done ? "bg-primary/50" : "bg-border"}`} />}
            </li>
          );
        })}
      </ol>
      <p className="text-xs"><span className="font-medium">{current ?? "—"}</span>{index != null && <span className="text-muted-foreground"> · stage {index + 1} of {stages.length}</span>}</p>
    </div>
  );
}
