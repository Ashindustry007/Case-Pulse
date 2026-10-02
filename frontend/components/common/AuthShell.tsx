import { Logo } from "./Logo";

/** Centered card on charcoal with a faint gold glow — shared by login and invite pages. */
export function AuthShell({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <main className="relative grid min-h-screen place-items-center overflow-hidden p-4">
      <div aria-hidden className="pointer-events-none absolute left-1/2 top-[-12rem] h-[34rem] w-[34rem] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
      <div className="relative w-full max-w-[22rem] space-y-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <Logo className="size-10" />
          <div>
            <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
            {subtitle && <p className="mt-1 text-[13px] text-muted-foreground">{subtitle}</p>}
          </div>
        </div>
        <div className="rounded-2xl border bg-card p-6 shadow-[0_20px_60px_-30px_rgba(0,0,0,0.6)]">{children}</div>
      </div>
    </main>
  );
}
