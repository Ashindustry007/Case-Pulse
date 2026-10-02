import Link from "next/link";
import { SourceDrawerProvider } from "@/components/citations/SourceDrawer";
import { SignOutButton } from "@/components/common/SignOutButton";

export default function AttorneyLayout({ children }: { children: React.ReactNode }) {
  return (
    <SourceDrawerProvider>
    <div className="min-h-screen">
      <header className="flex items-center gap-4 border-b px-4 py-2">
        <Link href="/matters" className="font-semibold">◉ Case Pulse</Link>
        <Link href="/matters" className="text-sm text-muted-foreground hover:text-foreground">Matters</Link>
        <Link href="/costs" className="text-sm text-muted-foreground hover:text-foreground">AI costs</Link>
        <span className="ml-auto text-xs text-muted-foreground">Attorney</span>
        <SignOutButton />
      </header>
      {children}
    </div>
    </SourceDrawerProvider>
  );
}
