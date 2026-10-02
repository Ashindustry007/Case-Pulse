import { Check } from "lucide-react";

/** Case stage as a labelled stepper: done = gold check, current = ringed gold, future = dim. Every stage is named. */
export function StageStepper({ stages, index, current }: { stages: string[]; index: number | null; current: string | null }) {
  if (!stages.length) return current ? <span className="text-sm">{current}</span> : null;
  return (
    <ol className="grid w-full" style={{ gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))` }} aria-label="Case stage">
      {stages.map((s, i) => {
        const done = index != null && i < index;
        const now = index === i;
        return (
          <li key={s} className="relative flex flex-col items-center gap-2 px-1 text-center" aria-current={now ? "step" : undefined}>
            {i < stages.length - 1 && (
              <span className={`absolute left-1/2 top-[11px] h-0.5 w-full ${done ? "bg-primary/60" : "bg-border"}`} aria-hidden />
            )}
            <span
              className={`relative z-10 grid size-6 place-items-center rounded-full text-[11px] font-semibold ${
                now ? "bg-primary text-primary-foreground ring-4 ring-primary/20" : done ? "bg-primary/20 text-primary" : "border bg-card text-muted-foreground"
              }`}
            >
              {done ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
            </span>
            <span className={`text-[11.5px] leading-tight ${now ? "font-semibold text-primary" : done ? "text-foreground" : "text-muted-foreground"}`}>{s}</span>
          </li>
        );
      })}
    </ol>
  );
}
