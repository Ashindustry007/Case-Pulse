import { describe, expect, it } from "vitest";
import { chipKey, chipLabel, chipText, locateSpan, uniqueCitations } from "./citations";

const c = (o: Partial<Parameters<typeof locateSpan>[1]> = {}) => ({
  record_id: "note:12", source_type: "note" as const, title: "t", char_start: 4, char_end: 9, excerpt: "quick", page: null, ...o,
});

describe("citations", () => {
  it("labels chips by type, id and page", () => {
    expect(chipLabel(c())).toBe("n12");
    expect(chipLabel(c({ record_id: "document:4", source_type: "document", page: 112 }))).toBe("d4 p112");
  });
  it("splits text at the cited span", () => {
    expect(locateSpan("the quick fox", c())).toEqual(["the ", "quick", " fox"]);
  });
  it("falls back to searching the excerpt when offsets drift", () => {
    expect(locateSpan("a quick fox", c())).toEqual(["a ", "quick", " fox"]);
  });
  it("clamps out-of-range offsets", () => {
    expect(locateSpan("abc", c({ char_start: 10, char_end: 20, excerpt: "zzz" }))).toEqual(["abc", "", ""]);
  });
  it("dedupes citations", () => {
    expect(uniqueCitations([c(), c(), c({ char_start: 0 })])).toHaveLength(2);
  });
  it("renders human chip text, never a raw id", () => {
    expect(chipText({ source_type: "note", title: "Call", date: "2026-09-09" })).toBe("Note · Sep 9");
    expect(chipText({ source_type: "document", title: "MRI Report - Lumbar.pdf", date: null, page: 3 })).toBe("MRI Report Lumbar · p3");
    expect(chipText({ source_type: "document", title: "05-medical-bills__created__acme-ortho-itemized-bill-2024-05-27.pdf", date: null, page: 1 })).toBe("acme ortho itemized… · p1");
    expect(chipText({ source_type: "medical_record", title: "x", date: null, page: 2 })).toBe("Records p2");
    expect(chipText({ source_type: "custom_field", title: "Custom field · Policy Limits", date: null })).toBe("Field · Policy Limits");
    expect(chipText({ source_type: "communication", title: "Re: claim", date: null })).toBe("Email");
    expect(chipText({ source_type: "note", title: "x", date: "2026-09-09" })).not.toMatch(/\d{5}/);
  });
  it("keys chips by record and page", () => {
    expect(chipKey({ record_id: "document:4", page: 2 })).toBe("document:4|2");
  });
});
