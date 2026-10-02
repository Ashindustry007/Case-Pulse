import Link from "next/link";
import { Cited } from "@/components/citations/Cited";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fmtDate, fmtMoneyShort } from "@/lib/format";
import type { Grant, Providers } from "@/lib/types";

export function ProvidersPanel({ matterId, providers, grants }: { matterId: number; providers?: Providers; grants?: Grant[] }) {
  return (
    <Card>
      <CardHeader className="pb-1"><CardTitle className="text-sm">👩‍⚕️ Providers · liens · shares</CardTitle></CardHeader>
      <CardContent>
        <ul className="space-y-2 text-sm">
          {providers?.providers.map((p) => {
            const g = grants?.find((x) => x.provider_contact_id === p.contact_id && !x.revoked_at);
            return (
              <li key={p.contact_id}>
                <span className="font-medium">{p.name}</span>{" "}
                <Cited value={p.billed} render={(v: number) => fmtMoneyShort(v)} />
                {p.lien && <Badge variant="outline" className="ml-1 text-[10px]">LIEN</Badge>}
                <span className="text-xs text-muted-foreground">
                  {" "}· balance <Cited value={p.balance} render={(v: number) => fmtMoneyShort(v)} />
                  {p.last_visit && ` · last visit ${fmtDate(p.last_visit)}`}
                  {p.current_gap_days != null && p.current_gap_days > 30 && ` · ${p.current_gap_days}d gap`}
                </span>
                <div className="text-xs">
                  {g?.latest_version
                    ? <Link className="underline" href={`/matters/${matterId}/share?provider=${p.contact_id}`}>v{g.latest_version} shared {fmtDate(g.released_at)} · opened {g.view_count}× [audit ▸]</Link>
                    : <Link className="underline" href={`/matters/${matterId}/share?provider=${p.contact_id}`}>Not shared · Share ▸</Link>}
                </div>
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}
