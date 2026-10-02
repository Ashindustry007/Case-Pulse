import { describe, expect, it } from "vitest";
import { roleFromToken, routeDecision } from "./route-guard";

const tok = (payload: object) =>
  `x.${Buffer.from(JSON.stringify(payload)).toString("base64url")}.y`;

describe("roleFromToken", () => {
  it("reads the role claim", () => {
    expect(roleFromToken(tok({ sub: "1", role: "provider", exp: Date.now() / 1000 + 60 }))).toBe("provider");
  });
  it("rejects expired, malformed and unknown roles", () => {
    expect(roleFromToken(tok({ role: "attorney", exp: 1 }))).toBeNull();
    expect(roleFromToken("garbage")).toBeNull();
    expect(roleFromToken(tok({ role: "admin" }))).toBeNull();
    expect(roleFromToken(undefined)).toBeNull();
  });
});

describe("routeDecision", () => {
  it("sends anonymous users to login with next", () => {
    expect(routeDecision("/matters/1", null)).toBe("/login?next=%2Fmatters%2F1");
    expect(routeDecision("/", null)).toBe("/login");
  });
  it("keeps each role in its own area", () => {
    expect(routeDecision("/matters", "provider")).toBe("/provider/cases");
    expect(routeDecision("/costs", "provider")).toBe("/provider/cases");
    expect(routeDecision("/provider/cases/1", "attorney")).toBe("/matters");
    expect(routeDecision("/login", "attorney")).toBe("/matters");
  });
  it("allows the right role through", () => {
    expect(routeDecision("/matters/1/share", "attorney")).toBeNull();
    expect(routeDecision("/provider/cases", "provider")).toBeNull();
    expect(routeDecision("/login", null)).toBeNull();
  });
});
