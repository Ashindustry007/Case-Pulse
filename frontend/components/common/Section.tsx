import type { LucideIcon } from "lucide-react";

/** Quiet labelled section: small uppercase label + icon, optional right-side action. */
export function Section({ icon: Icon, title, action, children, className = "" }: {
  icon?: LucideIcon; title: string; action?: React.ReactNode; children: React.ReactNode; className?: string;
}) {
  return (
    <section className={`space-y-3 ${className}`}>
      <div className="flex items-center gap-2">
        {Icon && <Icon className="size-3.5 text-muted-foreground" aria-hidden />}
        <h2 className="section-label">{title}</h2>
        {action && <div className="ml-auto text-xs">{action}</div>}
      </div>
      {children}
    </section>
  );
}

/** Raised surface for grouped content. */
export function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-xl border bg-card p-4 ${className}`}>{children}</div>;
}
