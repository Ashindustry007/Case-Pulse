import { describe, expect, it } from "vitest";
import { newState, plain, tokenize } from "./richtext";

describe("richtext", () => {
  it("turns **bold** into bold tokens without leaving asterisks", () => {
    const t = tokenize("**Pleadings uploaded:** The complaint was filed.");
    expect(t).toEqual([{ t: "text", s: "Pleadings uploaded:", b: true }, { t: "text", s: " The complaint was filed.", b: false }]);
    expect(plain("a **b** c")).toBe("a b c");
  });
  it("carries bold across segments", () => {
    const st = newState();
    const a = tokenize("**What the firm has", st);
    const b = tokenize(" spent: $1,410**", st);
    const c = tokenize(" across 5 expenses", st);
    expect([a, b, c].flat().map((k) => (k.t === "text" ? k.b : null))).toEqual([true, true, false]);
  });
  it("renders bullets at line starts, including at the start of a segment", () => {
    const st = newState();
    expect(tokenize("Intro:\n- one\n- two", st).filter((k) => k.t === "bullet")).toHaveLength(2);
    const next = tokenize("\n- three", st);
    expect(next.filter((k) => k.t === "bullet")).toHaveLength(1);
    expect(plain("1. first\n2. second")).toBe("• first • second");
  });
  it("collapses blank lines into one paragraph break and never emits leading breaks", () => {
    const t = tokenize("\n\nHello\n\nWorld");
    expect(t[0]).toEqual({ t: "text", s: "Hello", b: false });
    expect(t.some((k) => k.t === "br" && k.double)).toBe(true);
  });
  it("leaves plain text untouched", () => {
    expect(tokenize("Just a sentence.")).toEqual([{ t: "text", s: "Just a sentence.", b: false }]);
  });
  it("turns markdown table rows into readable lines", () => {
    expect(plain("| Date | Item | Amount |\n|---|---|---|\n| 2023-08-31 | Records copy | $65.00 |")).toBe("Date · Item · Amount 2023-08-31 · Records copy · $65.00");
    const st = newState();
    const a = tokenize("| 2023-08-31 | Records copy", st);
    const b = tokenize(" | $65.00 |", st);
    expect([...a, ...b].map((k) => (k.t === "text" ? k.s : "")).join("")).toBe("2023-08-31 · Records copy· $65.00");
  });
});
