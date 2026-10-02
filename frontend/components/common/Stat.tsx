import type { LucideIcon } from "lucide-react";

/** KPI tile: label · big value · supporting lines · optional details. Same anatomy for every tile. */
export function KpiTile({ icon: Icon, label, tag, value, children, className = "" }: {
  icon?: LucideIcon; label: string; tag?: string; value: React.ReactNode; children?: React.ReactNode; className?: string;
}) {
  return (
    <div className={`flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-4 ${className}`}>
      <div className="flex items-center gap-2">
        {Icon && <Icon className="size-3.5 text-muted-foreground" aria-hidden />}
        <p className="section-label">{label}</p>
        {tag && <span className="ml-auto rounded-full border px-2 py-px text-[10px] uppercase tracking-wider text-muted-foreground">{tag}</span>}
      </div>
      <div className="text-[28px] font-semibold leading-tight tracking-tight">{value}</div>
      {children && <div className="space-y-1.5 text-[13px] text-muted-foreground">{children}</div>}
    </div>
  );
}
