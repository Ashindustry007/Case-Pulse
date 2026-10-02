import { SignOutButton } from "@/components/common/SignOutButton";

export default function ProviderLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-muted/30">
      <header className="flex items-center justify-between border-b bg-background px-4 py-2">
        <span className="font-semibold">◉ Case Pulse</span>
        <SignOutButton />
      </header>
      <main className="mx-auto max-w-3xl p-3 sm:p-6">{children}</main>
    </div>
  );
}
