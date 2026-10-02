"use client";
import { ArrowLeft, Eye, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Chips } from "@/components/citations/CitationChip";
import { ErrorNote, Loading } from "@/components/common/states";
import { ProviderCaseView } from "@/components/provider/ProviderCaseView";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
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
  ["open_requests", "Open requests"], ["documents", "Documents / medical records"], ["case_details", "Case details"],
  ["adherence", "Treatment adherence"], ["other_care", "Other providers' care"],
];
const DEFAULT: Toggles = { fields: ["status", "open_requests"], document_ids: [], case_fields: [], coverage_detail: "confirmed", status_note: "" };

const toastError = (e: unknown) => toast.error(e instanceof ApiError ? e.message : String(e));

export function ShareComposer({ matterId, initialProvider }: { matterId: number; initialProvider?: number }) {
  const providers = useApi<Providers>(`/api/matters/${matterId}/providers`);
  const grants = useApi<Grant[]>(`/api/matters/${matterId}/shares`);
  const [contactId, setContactId] = useState<number | null>(initialProvider ?? null);
  const provider = providers.data?.providers.find((p) => p.contact_id === contactId);
  const grant = grants.data?.find((g) => g.provider_contact_id === contactId && !g.revoked_at);
  const auditGrant = grants.data?.filter((g) => g.provider_contact_id === contactId).reduce<Grant | undefined>((a, g) => (!a || g.id > a.id ? g : a), undefined);   // latest, even if revoked
  const q = contactId ? `provider_contact_id=${contactId}` : null;
  const candidates = useApi<ShareCandidates>(q && `/api/matters/${matterId}/share-candidates?${q}`);
  const reqs = useApi<ProviderRequest[]>(q && `/api/matters/${matterId}/requests?${q}`);
  const audit = useApi<ShareAudit>(auditGrant ? `/api/shares/${auditGrant.id}/audit` : null);
  const [email, setEmail] = useState("");
  const [t, setT] = useState<Toggles>(DEFAULT);
  const [flags, setFlags] = useState<DraftFlag[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (!contactId && providers.data?.providers[0]) setContactId(providers.data.providers[0].contact_id); }, [providers.data, contactId]);
  useEffect(() => { setEmail(grant?.email ?? provider?.email ?? ""); }, [contactId, grant?.email, provider?.email]);
  const last = audit.data?.versions.at(-1)?.policy;
  const resetKey = `${contactId}|${audit.data?.grant.id}|${last?.version}`;   // stable ids: audit reloads (dismiss) keep unsaved edits
  useEffect(() => {   // start from the latest released policy, if any
    setT(last ? { fields: last.fields, document_ids: last.document_ids, case_fields: last.case_fields ?? [], coverage_detail: last.coverage_detail, status_note: last.status_note ?? "" } : DEFAULT);
    setFlags([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey]);

  const preview = useMemo(() => (candidates.data ? applyPolicy(candidates.data, t) : null), [candidates.data, t]);
  const openFlags = flags.filter((f) => t.status_note.includes(f.text));   // a flag clears once its text is edited out
  const toggle = (f: ShareField, on: boolean) => setT((s) => {
    const fields = on ? [...s.fields, f] : s.fields.filter((x) => x !== f);
    // First time case details are switched on: pre-select only the details recommended as safe for providers.
    const case_fields = f === "case_details" && on && s.case_fields.length === 0
      ? (candidates.data?.case_detail_options ?? []).filter((o) => o.recommended).map((o) => o.id) : s.case_fields;
    return { ...s, fields, case_fields };
  });
  const toggleDetail = (id: string, on: boolean) => setT((s) => ({ ...s, case_fields: on ? [...s.case_fields, id] : s.case_fields.filter((x) => x !== id) }));
  const nextVersion = (grant?.latest_version ?? 0) + 1;

  async function draft() {
    if (!contactId) return;
    try {
      const d = await api<ProviderDraft>(`/api/matters/${matterId}/provider-draft`, { json: { provider_contact_id: contactId, fields: t.fields } });
      setT((s) => ({ ...s, status_note: d.draft }));
      setFlags(d.flags);
    } catch (e) { toastError(e); }
  }

  async function release() {
    if (!contactId || !email.trim()) { toast.error("Provider email is required."); return; }
    setBusy(true);
    try {
      const g = grant ?? await api<Grant>("/api/shares", { json: { matter_id: matterId, provider_contact_id: contactId, email: email.trim() } });
      const r = await api<ReleaseResult>(`/api/shares/${g.id}/release`, {
        json: {
          fields: t.fields, document_ids: t.fields.includes("documents") ? t.document_ids : [],
          case_fields: t.fields.includes("case_details") ? t.case_fields : [],
          coverage_detail: t.coverage_detail, status_note: t.status_note || null,
        },
      });
      toast.success(`Released v${r.policy.version}`);
      if (r.invite_url) toast(`Invite link (also in server console): ${r.invite_url}`, { duration: 20000 });
      grants.reload(); audit.reload();
    } catch (e) {
      toastError(e);
    } finally { setBusy(false); }
  }

  async function revoke() {
    if (!grant || !confirm(`Revoke ${grant.provider_name ?? "this provider"}'s access? They lose access immediately.`)) return;
    try {
      await api(`/api/shares/${grant.id}/revoke`, { method: "POST" });
      toast.success("Access revoked");
      grants.reload(); audit.reload();
    } catch (e) { toastError(e); }
  }

  async function dismiss(id: string) {
    try {
      await api(`/api/requests/${encodeURIComponent(id)}/dismiss`, { method: "POST" });
      reqs.reload(); candidates.reload(); audit.reload();
    } catch (e) { toastError(e); }
  }

  return (
    <div className="mx-auto max-w-[1280px] px-4 py-6 sm:px-6">
      <Link href={`/matters/${matterId}`} className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground"><ArrowLeft className="size-3.5" /> Back to matter</Link>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">Share with a provider</h1>
      <p className="mt-1 text-[13px] text-muted-foreground">Choose exactly what they see. The preview on the right is the same page they will get.</p>

      <div className="mt-6 grid gap-6 lg:grid-cols-[400px_minmax(0,1fr)]">
        <div className="space-y-4">
          <Step n={1} title="Recipient">
            <select className="h-9 w-full rounded-lg border bg-background px-2.5 text-sm" value={contactId ?? ""} onChange={(e) => setContactId(Number(e.target.value))}>
              {providers.data?.providers.map((p) => <option key={p.contact_id} value={p.contact_id}>{p.name}</option>)}
            </select>
            <Input type="email" placeholder="provider@clinic.com" value={email} disabled={!!grant} onChange={(e) => setEmail(e.target.value)} />
            <p className="text-xs text-muted-foreground">{grant?.latest_version ? `Current version v${grant.latest_version}, released ${fmtDate(grant.released_at)}` : "Not shared yet"}</p>
          </Step>

          <Step n={2} title="What to share">
            <div className="space-y-2.5 text-[13.5px]">
              {FIELDS.map(([f, label]) => (
                <div key={f}>
                  <label className="flex cursor-pointer items-center gap-2.5"><Checkbox checked={t.fields.includes(f)} onCheckedChange={(v) => toggle(f, v === true)} />{label}</label>
                  {f === "coverage" && t.fields.includes("coverage") && (
                    <RadioGroup className="ml-7 mt-1.5" value={t.coverage_detail} onValueChange={(v) => setT((s) => ({ ...s, coverage_detail: v as Toggles["coverage_detail"] }))}>
                      <label className="flex items-center gap-2"><RadioGroupItem value="confirmed" />Confirmed only</label>
                      <label className="flex items-center gap-2"><RadioGroupItem value="limits" />Carrier + limits</label>
                    </RadioGroup>
                  )}
                  {f === "documents" && t.fields.includes("documents") && (
                    <div className="ml-7 mt-1.5 max-h-52 space-y-1.5 overflow-y-auto pr-1">
                      {candidates.data?.available_documents.map((d) => (
                        <label key={d.id} className="flex cursor-pointer items-start gap-2 text-xs">
                          <Checkbox checked={t.document_ids.includes(d.id)} onCheckedChange={(v) => setT((s) => ({ ...s, document_ids: v === true ? [...s.document_ids, d.id] : s.document_ids.filter((x) => x !== d.id) }))} />
                          <span className="min-w-0">{d.title}{d.page_count && ` (${d.page_count} pp)`}{d.category && <span className="ml-1.5 rounded bg-muted px-1 text-[10px] text-muted-foreground">{d.category}</span>}</span>
                        </label>
                      ))}
                    </div>
                  )}
                  {f === "case_details" && t.fields.includes("case_details") && (
                    <div className="ml-7 mt-1.5 max-h-64 space-y-1.5 overflow-y-auto pr-1">
                      {(candidates.data?.case_detail_options ?? []).length === 0 && <p className="text-xs text-muted-foreground">No case details in the file.</p>}
                      {candidates.data?.case_detail_options?.map((o) => (
                        <label key={o.id} className="flex cursor-pointer items-start gap-2 text-xs" title={o.value}>
                          <Checkbox checked={t.case_fields.includes(o.id)} onCheckedChange={(v) => toggleDetail(o.id, v === true)} />
                          <span className="min-w-0">
                            <span className="font-medium">{o.label}</span>
                            <span className="block truncate text-muted-foreground">{o.value}</span>
                            {o.confidential && <span className="text-warning">Confidential — not recommended for providers</span>}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Step>

          <Step n={3} title="Status note" action={<Button size="sm" variant="outline" onClick={draft}><Sparkles /> Draft with AI</Button>}>
            <Textarea rows={4} value={t.status_note} onChange={(e) => setT((s) => ({ ...s, status_note: e.target.value }))} />
            {openFlags.length === 0
              ? <p className="text-xs text-success">No confidential content flagged</p>
              : <ul className="space-y-1 text-xs text-danger">{openFlags.map((f, i) => <li key={i}>“{f.text}” — {f.reason}</li>)}</ul>}
          </Step>

          <Step n={4} title="Open requests (attorney view)">
            <div className="space-y-2 text-[13px]">
              {reqs.data?.length === 0 && <p className="text-muted-foreground">None for this provider.</p>}
              {reqs.data?.map((r) => (
                <div key={r.id} className="flex items-start gap-2">
                  <span className={r.state !== "open" ? "text-muted-foreground line-through" : ""}>{r.description}<Chips citations={r.citations} /></span>
                  <span className="ml-auto shrink-0 text-xs text-muted-foreground">{r.state}</span>
                  {r.state === "open" && <Button size="sm" variant="ghost" className="h-6 px-2" onClick={() => dismiss(r.id)}>Dismiss</Button>}
                </div>
              ))}
            </div>
          </Step>

          <div className="sticky bottom-0 -mx-1 flex gap-2 border-t bg-background/90 px-1 py-3 backdrop-blur">
            {grant && <Button variant="outline" onClick={revoke}>Revoke</Button>}
            <Button className="ml-auto" disabled={busy || !contactId || openFlags.length > 0} onClick={release}>Release v{nextVersion} &amp; notify</Button>
          </div>
        </div>

        <div className="min-w-0 space-y-6">
          <div className="overflow-hidden rounded-2xl border bg-card">
            <div className="flex items-center gap-2 border-b px-4 py-2.5 text-[13px]">
              <Eye className="size-4 text-primary" /> <span className="font-medium">Provider view</span>
              <span className="text-muted-foreground">· exactly what {provider?.name ?? "the provider"} will see</span>
              <span className="ml-auto rounded-full bg-primary/15 px-2 py-0.5 text-[10px] uppercase tracking-wider text-primary">Live preview</span>
            </div>
            <div className="max-h-[calc(100vh-14rem)] overflow-y-auto bg-background p-5">
              <ErrorNote error={candidates.error} />
              {preview ? <ProviderCaseView c={preview} preview /> : contactId ? <Loading lines={6} /> : <p className="text-muted-foreground">Pick a provider.</p>}
            </div>
          </div>
          {audit.data && (
            <div className="rounded-xl border bg-card p-4">
              <p className="section-label mb-3">History &amp; audit</p>
              <AuditTimeline audit={audit.data} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Step({ n, title, action, children }: { n: number; title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="space-y-3 rounded-xl border bg-card p-4">
      <div className="flex items-center gap-2.5">
        <span className="grid size-5 place-items-center rounded-full bg-primary/15 text-[11px] font-semibold text-primary">{n}</span>
        <h2 className="text-sm font-medium">{title}</h2>
        {action && <div className="ml-auto">{action}</div>}
      </div>
      {children}
    </section>
  );
}
