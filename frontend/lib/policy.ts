/** Client mirror of backend sharing/projection.py:project(). Keep the two in lockstep; tests pin both. */
import type { ProviderCase, ShareCandidates, ShareField } from "./types";

export type Toggles = { fields: ShareField[]; document_ids: string[]; coverage_detail: "confirmed" | "limits"; status_note: string };

const SECTIONS = ["heartbeat", "coverage", "case_value", "bills", "requests", "documents", "adherence", "other_care", "status_note", "shared_by", "updated_at"] as const;

export function applyPolicy(c: ShareCandidates, t: Toggles): ProviderCase {
  const out: Record<string, unknown> = { ...c.case };
  for (const k of SECTIONS) delete out[k];
  const on = new Set(t.fields);
  const put = (k: string, v: unknown) => { if (v != null) out[k] = v; };
  put("status_note", t.status_note.trim() || null);
  if (on.has("status")) put("heartbeat", c.case.heartbeat);
  if (on.has("coverage")) put("coverage", c.coverage_variants[t.coverage_detail]);
  if (on.has("case_value")) put("case_value", c.case.case_value);
  if (on.has("bills")) put("bills", c.case.bills);
  if (on.has("open_requests")) put("requests", (c.case.requests ?? []).filter((r) => r.state !== "dismissed"));
  if (on.has("documents")) { const ids = new Set(t.document_ids); put("documents", c.available_documents.filter((d) => ids.has(d.id))); }
  if (on.has("adherence")) put("adherence", c.case.adherence);
  if (on.has("other_care")) put("other_care", c.case.other_care?.length ? c.case.other_care : null);
  return out as ProviderCase;
}
