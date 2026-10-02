import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const assign = vi.fn();
const json = (status: number) => new Response("{}", { status });

async function loadApi() {
  vi.resetModules();
  return (await import("./api")).api;
}

beforeEach(() => {
  assign.mockReset();
  vi.stubGlobal("window", { location: { assign, pathname: "/matters/1" } });
});
afterEach(() => vi.unstubAllGlobals());

describe("api 401 handling", () => {
  it("logs out to clear the cookie, then redirects to login with next", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json(401)).mockResolvedValueOnce(json(200));
    vi.stubGlobal("fetch", fetchMock);
    const api = await loadApi();
    await expect(api("/api/matters")).rejects.toMatchObject({ status: 401 });
    await vi.waitFor(() => expect(assign).toHaveBeenCalledWith("/login?next=%2Fmatters%2F1"));
    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toMatch(/\/api\/auth\/logout$/);
    expect(init).toMatchObject({ method: "POST", credentials: "include" });
  });
  it("still redirects when the logout call fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(json(401)).mockRejectedValueOnce(new Error("down")));
    const api = await loadApi();
    await expect(api("/api/matters")).rejects.toMatchObject({ status: 401 });
    await vi.waitFor(() => expect(assign).toHaveBeenCalledTimes(1));
  });
  it("does not redirect for auth endpoints or loop on concurrent 401s", async () => {
    const fetchMock = vi.fn().mockImplementation(async (url: string) => (url.endsWith("/logout") ? json(200) : json(401)));
    vi.stubGlobal("fetch", fetchMock);
    const api = await loadApi();
    await expect(api("/api/auth/login", { json: {} })).rejects.toMatchObject({ status: 401 });
    expect(assign).not.toHaveBeenCalled();
    await Promise.allSettled([api("/api/a"), api("/api/b")]);
    await vi.waitFor(() => expect(assign).toHaveBeenCalledTimes(1));
    expect(fetchMock.mock.calls.filter(([u]) => String(u).endsWith("/logout"))).toHaveLength(1);
  });
});
