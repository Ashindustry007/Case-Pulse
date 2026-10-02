"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { SignOutButton } from "./SignOutButton";
import { ThemeToggle } from "./ThemeToggle";

type NavItem = { href: string; label: string };

/** Slim sticky top bar shared by the attorney and provider apps (no attorney-only imports). */
export function AppBar({ home, nav = [], role }: { home: string; nav?: NavItem[]; role: string }) {
  const path = usePathname() ?? "";
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-12 max-w-[1600px] items-center gap-5 px-4">
        <Link href={home} className="flex items-center gap-2 font-semibold tracking-tight">
          <Logo /> <span>Case Pulse</span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {nav.map((n) => {
            const active = path === n.href || (n.href !== home && path.startsWith(n.href));
            return (
              <Link
                key={n.href} href={n.href} aria-current={active ? "page" : undefined}
                className={`rounded-md px-2.5 py-1 transition-colors ${active ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"}`}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-1">
          <span className="mr-1 hidden rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wider text-muted-foreground sm:inline">{role}</span>
          <ThemeToggle />
          <SignOutButton />
        </div>
      </div>
    </header>
  );
}
