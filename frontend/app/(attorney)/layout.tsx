import { AppBar } from "@/components/common/AppBar";
import { SourceDrawerProvider } from "@/components/citations/SourceDrawer";

export default function AttorneyLayout({ children }: { children: React.ReactNode }) {
  return (
    <SourceDrawerProvider>
      <div className="min-h-screen">
        <AppBar home="/matters" role="Attorney" nav={[{ href: "/matters", label: "Matters" }, { href: "/costs", label: "AI costs" }]} />
        {children}
      </div>
    </SourceDrawerProvider>
  );
}
