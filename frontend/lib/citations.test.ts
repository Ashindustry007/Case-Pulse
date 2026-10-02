import { describe, expect, it } from "vitest";
import { chipLabel, locateSpan, uniqueCitations } from "./citations";

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
});
