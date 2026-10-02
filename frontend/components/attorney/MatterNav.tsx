"use client";
import { CalendarRange, Gauge, LayoutDashboard, MessageSquare, Share2, Stethoscope, User, Wallet } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { buttonVariants } from "@/components/ui/button";
import { apiUrl } from "@/lib/api";
import type { Overview } from "@/lib/types";
import { useApi } from "@/lib/use-api";

const ITEMS = [
  { seg: "", label: "Overview", icon: LayoutDashboard },
  { seg: "ask", label: "Ask the case", icon: MessageSquare },
  { seg: "timeline", label: "Timeline", icon: CalendarRange },
  { seg: "medical", label: "Medical", icon: Stethoscope },
  { seg: "money", label: "Money", icon: Wallet },
  { seg: "share", label: "Share", icon: Share2 },
  { seg: "ai-cost", label: "AI cost", icon: Gauge },
] as const;

function useActive(matterId: number) {
  const path = usePathname() ?? "";
  const base = `/matters/${matterId}`;
  return (seg: string) => (seg ? path.startsWith(`${base}/${seg}`) : path === base);
}

/** Matter sidebar: who the case is about, then one link per view (the overview no longer holds everything). */
export function MatterSidebar({ matterId }: { matterId: number }) {
  const o = useApi<Overview>(`/api/matters/${matterId}/overview`).data;
  const active = useActive(matterId);
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r bg-sidebar/60 md:flex">
      <div className="flex items-center gap-3 border-b px-4 py-4">
        {o?.client.photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={apiUrl(o.client.photo_url)} alt="" className="size-9 rounded-full object-cover ring-1 ring-border" />
        ) : <div className="grid size-9 place-items-center rounded-full bg-muted"><User className="size-4 text-muted-foreground" /></div>}
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold">{o?.client.name ?? "…"}</p>
          <p className="truncate text-xs text-muted-foreground">{o ? [o.matter.display_number, o.stage.current].filter(Boolean).join(" · ") : " "}</p>
        </div>
      </div>
      <nav className="flex-1 space-y-0.5 p-2">
        {ITEMS.map(({ seg, label, icon: Icon }) => {
          const on = active(seg);
          return (
            <Link
              key={seg} href={`/matters/${matterId}${seg ? `/${seg}` : ""}`} aria-current={on ? "page" : undefined}
              className={`relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13.5px] transition-colors ${on ? "bg-accent font-medium text-foreground" : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"}`}
            >
              {on && <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary" aria-hidden />}
              <Icon className={`size-4 ${on ? "text-primary" : ""}`} aria-hidden /> {label}
            </Link>
          );
        })}
      </nav>
      <div className="m-3 rounded-xl border bg-card p-3">
        <p className="text-[13px] font-medium">Provider portal</p>
        <p className="mt-0.5 text-xs leading-snug text-muted-foreground">Choose exactly what a provider can see on this case.</p>
        <Link href={`/matters/${matterId}/share`} className={buttonVariants({ size: "sm", className: "mt-2.5 w-full" })}><Share2 /> Share with provider</Link>
      </div>
    </aside>
  );
}

/** Same links as a scrollable strip on small screens. */
export function MatterTabsMobile({ matterId }: { matterId: number }) {
  const active = useActive(matterId);
  return (
    <nav className="flex gap-1 overflow-x-auto border-b px-3 py-2 md:hidden">
      {ITEMS.map(({ seg, label, icon: Icon }) => (
        <Link
          key={seg} href={`/matters/${matterId}${seg ? `/${seg}` : ""}`}
          className={`flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-[13px] ${active(seg) ? "bg-accent text-foreground" : "text-muted-foreground"}`}
        >
          <Icon className="size-3.5" aria-hidden /> {label}
        </Link>
      ))}
    </nav>
  );
}

/** Standard page frame for matter sub-pages. */
export function MatterPage({ title, subtitle, action, children, wide = false }: {
  title: string; subtitle?: string; action?: React.ReactNode; children: React.ReactNode; wide?: boolean;
}) {
  return (
    <div className={`mx-auto space-y-6 px-4 py-6 sm:px-6 ${wide ? "max-w-[1280px]" : "max-w-[1120px]"}`}>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="mt-0.5 text-[13px] text-muted-foreground">{subtitle}</p>}
        </div>
        {action && <div className="ml-auto">{action}</div>}
      </div>
      {children}
    </div>
  );
}
