import { describe, expect, it } from "vitest";
import { applyPolicy, type Toggles } from "./policy";
import type { ShareCandidates } from "./types";

const candidates = {
  provider: { contact_id: 600, name: "Provider A" },
  coverage_variants: { confirmed: { confirmed: true }, limits: { confirmed: true, carrier: "Acme", limits_text: "BI per person $100,000" } },
  available_documents: [{ id: "document:10", title: "Report" }, { id: "document:11", title: "Memo" }],
  case_detail_options: [
    { id: "custom_field:1:a", label: "Date of Incident", value: "2023-04-23", confidential: false, recommended: true },
    { id: "custom_field:1:b", label: "Case Value Rationale", value: "secret", confidential: true, recommended: false },
  ],
  case: {
    grant_id: 0, policy_version: 0, patient_display: "P. E.", firm_name: "Firm",
    heartbeat: { state: "active", recent_movement: [] },
    coverage: { confirmed: true, carrier: "Acme", limits_text: "x" },
    case_value: { label: "Estimate", low: 1, high: 2 },
    bills: { billed: 10, lien: false, items: [] },
    requests: [{ id: "r1", kind: "records", description: "d", state: "open", citations: [] },
               { id: "r2", kind: "bills", description: "d", state: "dismissed", citations: [] }],
    documents: [{ id: "document:10", title: "Report" }, { id: "document:11", title: "Memo" }],
    adherence: { visits: ["2026-09-01"], gaps: [] },
    other_care: [],
  },
} as unknown as ShareCandidates;

const t = (o: Partial<Toggles>): Toggles => ({ fields: [], document_ids: [], case_fields: [], coverage_detail: "confirmed", status_note: "", ...o });

describe("applyPolicy", () => {
  it("keeps only identity keys when nothing is toggled", () => {
    expect(Object.keys(applyPolicy(candidates, t({}))).sort()).toEqual(["firm_name", "grant_id", "patient_display", "policy_version"]);
  });
  it("adds exactly the toggled sections", () => {
    const c = applyPolicy(candidates, t({ fields: ["status", "bills"] }));
    expect(c.heartbeat?.state).toBe("active");
    expect(c.bills?.billed).toBe(10);
    expect("coverage" in c).toBe(false);
    expect("case_value" in c).toBe(false);
  });
  it("uses the chosen coverage variant", () => {
    expect(applyPolicy(candidates, t({ fields: ["coverage"] })).coverage).toEqual({ confirmed: true });
    expect(applyPolicy(candidates, t({ fields: ["coverage"], coverage_detail: "limits" })).coverage?.carrier).toBe("Acme");
  });
  it("filters documents to the picked ids and drops dismissed requests", () => {
    const c = applyPolicy(candidates, t({ fields: ["documents", "open_requests"], document_ids: ["document:11"] }));
    expect(c.documents?.map((d) => d.id)).toEqual(["document:11"]);
    expect(c.requests?.map((r) => r.id)).toEqual(["r1"]);
  });
  it("omits empty other-care and includes a trimmed status note", () => {
    const c = applyPolicy(candidates, t({ fields: ["other_care"], status_note: "  Hi  " }));
    expect("other_care" in c).toBe(false);
    expect(c.status_note).toBe("Hi");
  });
  it("shares only the chosen case details, as label/value pairs", () => {
    const c = applyPolicy(candidates, t({ fields: ["case_details"], case_fields: ["custom_field:1:a"] }));
    expect(c.case_details).toEqual([{ label: "Date of Incident", value: "2023-04-23" }]);
    expect("case_details" in applyPolicy(candidates, t({ case_fields: ["custom_field:1:a"] }))).toBe(false);
  });
});
