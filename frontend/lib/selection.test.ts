import { describe, expect, it } from "vitest";
import { selectionSources } from "./selection";

const cite = (id: string) => ({ record_id: id, source_type: "note" as const, title: id, char_start: 0, char_end: 1, excerpt: "x" });
const segs = [
  { id: "s1", text: "MRI confirms a herniation", citations: [cite("document:1")] },
  { id: "s2", text: " and ", citations: [] },
  { id: "s3", text: "PT for strain", citations: [cite("note:2"), cite("document:1")] },
];

describe("selectionSources", () => {
  it("unions citations of the selected segments", () => {
    const r = selectionSources(segs, ["s1", "s3"]);
    expect(r.citations.map((c) => c.record_id)).toEqual(["document:1", "note:2"]);
    expect(r.needsVerify).toBe(false);
  });
  it("asks to verify when an uncited segment is selected", () => {
    expect(selectionSources(segs, ["s2"]).needsVerify).toBe(true);
    expect(selectionSources(segs, ["s2"]).citations).toEqual([]);
  });
  it("ignores unknown ids", () => {
    expect(selectionSources(segs, ["zz"])).toEqual({ citations: [], needsVerify: false });
  });
});
