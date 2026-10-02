import { AppBar } from "@/components/common/AppBar";

export default function ProviderLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <AppBar home="/provider/cases" role="Provider" />
      <main className="mx-auto max-w-2xl px-4 py-6 sm:py-8">{children}</main>
    </div>
  );
}
