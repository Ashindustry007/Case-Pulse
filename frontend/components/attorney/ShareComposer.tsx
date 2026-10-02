"use client";
import { Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Chips } from "@/components/citations/CitationChip";
import { ErrorNote, Loading } from "@/components/common/states";
import { ProviderCaseView } from "@/components/provider/ProviderCaseView";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { applyPolicy, type Toggles } from "@/lib/policy";
import type { DraftFlag, Grant, ProviderDraft, ProviderRequest, Providers, ReleaseResult, ShareAudit, ShareCandidates, ShareField } from "@/lib/types";
import { useApi } from "@/lib/use-api";
import { AuditTimeline } from "./AuditTimeline";

const FIELDS: [ShareField, string][] = [
  ["status", "Status & heartbeat"], ["coverage", "Coverage"], ["case_value", "Case value"], ["bills", "Their bills"],
  ["open_requests", "Open requests"], ["documents", "Documents"], ["adherence", "Treatment adherence"], ["other_care", "Other providers' care"],
];
const DEFAULT: Toggles = { fields: ["status", "open_requests"], document_ids: [], coverage_detail: "confirmed", status_note: "" };

export function ShareComposer({ matterId, initialProvider }: { matterId: number; initialProvider?: number }) {
  const providers = useApi<Providers>(`/api/matters/${matterId}/providers`);
  const grants = useApi<Grant[]>(`/api/matters/${matterId}/shares`);
  const [contactId, setContactId] = useState<number | null>(initialProvider ?? null);
  const provider = providers.data?.providers.find((p) => p.contact_id === contactId);
  const grant = grants.data?.find((g) => g.provider_contact_id === contactId && !g.revoked_at);
  const q = contactId ? `provider_contact_id=${contactId}` : null;
  const candidates = useApi<ShareCandidates>(q && `/api/matters/${matterId}/share-candidates?${q}`);
  const reqs = useApi<ProviderRequest[]>(q && `/api/matters/${matterId}/requests?${q}`);
  const audit = useApi<ShareAudit>(grant ? `/api/shares/${grant.id}/audit` : null);
  const [email, setEmail] = useState("");
  const [t, setT] = useState<Toggles>(DEFAULT);
  const [flags, setFlags] = useState<DraftFlag[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (!contactId && providers.data?.providers[0]) setContactId(providers.data.providers[0].contact_id); }, [providers.data, contactId]);
  useEffect(() => { setEmail(grant?.email ?? provider?.email ?? ""); }, [contactId, grant?.email, provider?.email]);
  useEffect(() => {   // start from the latest released policy, if any
    const last = audit.data?.versions.at(-1)?.policy;
    setT(last ? { fields: last.fields, document_ids: last.document_ids, coverage_detail: last.coverage_detail, status_note: last.status_note ?? "" } : DEFAULT);
    setFlags([]);
  }, [audit.data, contactId]);

  const preview = useMemo(() => (candidates.data ? applyPolicy(candidates.data, t) : null), [candidates.data, t]);
  const openFlags = flags.filter((f) => t.status_note.includes(f.text));   // a flag clears once its text is edited out
  const toggle = (f: ShareField, on: boolean) => setT((s) => ({ ...s, fields: on ? [...s.fields, f] : s.fields.filter((x) => x !== f) }));
  const nextVersion = (grant?.latest_version ?? 0) + 1;

  async function draft() {
    if (!contactId) return;
    const d = await api<ProviderDraft>(`/api/matters/${matterId}/provider-draft`, { json: { provider_contact_id: contactId, fields: t.fields } });
    setT((s) => ({ ...s, status_note: d.draft }));
    setFlags(d.flags);
  }

  async function release() {
    if (!contactId || !email.trim()) { toast.error("Provider email is required."); return; }
    setBusy(true);
    try {
      const g = grant ?? await api<Grant>("/api/shares", { json: { matter_id: matterId, provider_contact_id: contactId, email: email.trim() } });
      const r = await api<ReleaseResult>(`/api/shares/${g.id}/release`, {
        json: { fields: t.fields, document_ids: t.fields.includes("documents") ? t.document_ids : [], coverage_detail: t.coverage_detail, status_note: t.status_note || null },
      });
      toast.success(`Released v${r.policy.version}`);
      if (r.invite_url) toast(`Invite link (also in server console): ${r.invite_url}`, { duration: 20000 });
      grants.reload(); audit.reload();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : String(e));
    } finally { setBusy(false); }
  }

  async function revoke() {
    if (!grant || !confirm(`Revoke ${grant.provider_name ?? "this provider"}'s access? They lose access immediately.`)) return;
    await api(`/api/shares/${grant.id}/revoke`, { method: "POST" });
    toast.success("Access revoked");
    grants.reload();
  }

  async function dismiss(id: string) {
    await api(`/api/requests/${encodeURIComponent(id)}/dismiss`, { method: "POST" });
    reqs.reload(); candidates.reload(); audit.reload();
  }

  return (
    <div className="grid grid-cols-[360px_1fr] gap-4 p-4">
      <div className="space-y-4">
        <Card><CardContent className="space-y-2 pt-4 text-sm">
          <Label>Share with</Label>
          <select className="w-full rounded border bg-background p-2" value={contactId ?? ""} onChange={(e) => setContactId(Number(e.target.value))}>
            {providers.data?.providers.map((p) => <option key={p.contact_id} value={p.contact_id}>{p.name}</option>)}
          </select>
          <Input type="email" placeholder="provider@clinic.com" value={email} disabled={!!grant} onChange={(e) => setEmail(e.target.value)} />
          <p className="text-xs text-muted-foreground">{grant?.latest_version ? `current: v${grant.latest_version} (${fmtDate(grant.released_at)})` : "not shared yet"}</p>
        </CardContent></Card>

        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-sm">Fields</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            {FIELDS.map(([f, label]) => (
              <div key={f}>
                <label className="flex items-center gap-2"><Checkbox checked={t.fields.includes(f)} onCheckedChange={(v) => toggle(f, v === true)} />{label}</label>
                {f === "coverage" && t.fields.includes("coverage") && (
                  <RadioGroup className="ml-6 mt-1" value={t.coverage_detail} onValueChange={(v) => setT((s) => ({ ...s, coverage_detail: v as Toggles["coverage_detail"] }))}>
                    <label className="flex items-center gap-2"><RadioGroupItem value="confirmed" />Confirmed only</label>
                    <label className="flex items-center gap-2"><RadioGroupItem value="limits" />Carrier + limits</label>
                  </RadioGroup>
                )}
                {f === "documents" && t.fields.includes("documents") && (
                  <div className="ml-6 mt-1 space-y-1">
                    {candidates.data?.available_documents.map((d) => (
                      <label key={d.id} className="flex items-center gap-2 text-xs">
                        <Checkbox checked={t.document_ids.includes(d.id)} onCheckedChange={(v) => setT((s) => ({ ...s, document_ids: v === true ? [...s.document_ids, d.id] : s.document_ids.filter((x) => x !== d.id) }))} />
                        {d.title}{d.page_count && ` (${d.page_count} pp)`}
                      </label>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center pb-1">
            <CardTitle className="text-sm">Status note</CardTitle>
            <Button size="sm" variant="outline" className="ml-auto" onClick={draft}><Sparkles className="mr-1 h-3 w-3" />Draft with AI</Button>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Textarea rows={4} value={t.status_note} onChange={(e) => setT((s) => ({ ...s, status_note: e.target.value }))} />
            {openFlags.length === 0
              ? <p className="text-xs text-emerald-700">✔ 0 confidential flags</p>
              : <ul className="text-xs text-destructive">{openFlags.map((f, i) => <li key={i}>⚠ “{f.text}” — {f.reason}</li>)}</ul>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-sm">Open requests (attorney view)</CardTitle></CardHeader>
          <CardContent className="space-y-1 text-xs">
            {reqs.data?.length === 0 && <p className="text-muted-foreground">None for this provider.</p>}
            {reqs.data?.map((r) => (
              <div key={r.id} className="flex items-start gap-2">
                <span className={r.state !== "open" ? "text-muted-foreground line-through" : ""}>{r.description}<Chips citations={r.citations} /></span>
                <span className="ml-auto text-muted-foreground">{r.state}</span>
                {r.state === "open" && <Button size="sm" variant="ghost" className="h-6 px-2" onClick={() => dismiss(r.id)}>Dismiss</Button>}
              </div>
            ))}
          </CardContent>
        </Card>

        <div className="flex gap-2">
          {grant && <Button variant="outline" onClick={revoke}>Revoke</Button>}
          <Button className="ml-auto" disabled={busy || !contactId || openFlags.length > 0} onClick={release}>Release v{nextVersion} &amp; notify ▸</Button>
        </div>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader className="pb-1"><CardTitle className="text-sm">Preview: exactly what {provider?.name ?? "the provider"} will see</CardTitle></CardHeader>
          <CardContent className="rounded bg-muted/30 p-4">
            <ErrorNote error={candidates.error} />
            {preview ? <ProviderCaseView c={preview} preview /> : contactId ? <Loading lines={6} /> : <p className="text-muted-foreground">Pick a provider.</p>}
          </CardContent>
        </Card>
        {audit.data && (
          <Card>
            <CardHeader className="pb-1"><CardTitle className="text-sm">History / audit</CardTitle></CardHeader>
            <CardContent><AuditTimeline audit={audit.data} /></CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
