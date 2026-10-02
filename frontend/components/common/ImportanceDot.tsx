/** 1–10 importance as a small chip: 9–10 solid gold, 7–8 tinted, lower muted. */
export function Importance({ n }: { n?: number | null }) {
  if (n == null) return <span className="grid size-5 place-items-center text-xs text-muted-foreground">–</span>;
  const tone = n >= 9 ? "bg-primary text-primary-foreground" : n >= 7 ? "bg-primary/15 text-primary" : "bg-muted text-muted-foreground";
  return <span title={`Importance ${n}/10`} className={`grid size-5 shrink-0 place-items-center rounded-md text-[11px] font-semibold ${tone}`}>{n}</span>;
}
