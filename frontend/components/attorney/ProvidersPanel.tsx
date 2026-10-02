import { Users } from "lucide-react";
import Link from "next/link";
import { Cited } from "@/components/citations/Cited";
import { Panel, Section } from "@/components/common/Section";
import { fmtDate, fmtMoneyShort } from "@/lib/format";
import type { Grant, Providers } from "@/lib/types";

export function ProvidersPanel({ matterId, providers, grants }: { matterId: number; providers?: Providers; grants?: Grant[] }) {
  return (
    <Section icon={Users} title="Providers · liens · sharing">
      <Panel className="overflow-x-auto p-0">
        <table className="w-full min-w-[520px] text-[13px]">
          <thead>
            <tr className="border-b text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <th className="px-4 py-2 font-medium">Provider</th>
              <th className="px-2 py-2 text-right font-medium">Billed</th>
              <th className="px-2 py-2 text-right font-medium">Balance</th>
              <th className="px-4 py-2 text-right font-medium">Shared</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {providers?.providers.map((p) => {
              const g = grants?.find((x) => x.provider_contact_id === p.contact_id && !x.revoked_at);
              const href = `/matters/${matterId}/share?provider=${p.contact_id}`;
              return (
                <tr key={p.contact_id} className="align-top hover:bg-accent/30">
                  <td className="px-4 py-2.5">
                    <p className="font-medium leading-snug">{p.name}{p.lien && <span className="ml-2 rounded-full border border-warning/40 px-1.5 py-px text-[10px] uppercase tracking-wider text-warning">lien</span>}</p>
                    {p.last_visit && <p className="text-xs text-muted-foreground">last visit {fmtDate(p.last_visit)}</p>}
                  </td>
                  <td className="px-2 py-2.5 text-right"><Cited value={p.billed} render={(v: number) => fmtMoneyShort(v)} /></td>
                  <td className="px-2 py-2.5 text-right"><Cited value={p.balance} render={(v: number) => fmtMoneyShort(v)} /></td>
                  <td className="px-4 py-2.5 text-right">
                    {g?.latest_version
                      ? <Link href={href} className="text-primary hover:underline">v{g.latest_version} · opened {g.view_count}×</Link>
                      : <Link href={href} className="text-muted-foreground hover:text-primary hover:underline">Share…</Link>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
    </Section>
  );
}
