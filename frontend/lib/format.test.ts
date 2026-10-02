import { describe, expect, it } from "vitest";
import { daysAgo, fmtDate, fmtMoney, fmtMoneyShort, parseISODate } from "./format";

describe("format", () => {
  it("keeps date-only strings on their calendar day in any timezone", () => {
    const d = parseISODate("2026-09-28");
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 8, 28]);
    expect(fmtDate("2026-09-28")).toBe("Sep 28, 2026");
  });
  it("formats money", () => {
    expect(fmtMoney(22140)).toBe("$22,140");
    expect(fmtMoneyShort(84200)).toBe("$84.2k");
    expect(fmtMoneyShort(150000)).toBe("$150k");
    expect(fmtMoneyShort(950)).toBe("$950");
  });
  it("counts whole days ago", () => {
    expect(daysAgo("2026-09-29", new Date(2026, 9, 2, 15))).toBe(3);
  });
  it("renders empty for missing dates", () => {
    expect(fmtDate(null)).toBe("");
  });
});
