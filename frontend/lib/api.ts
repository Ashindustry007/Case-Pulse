export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** API-relative paths ("/api/...") → absolute URL; absolute URLs pass through. */
export const apiUrl = (path: string) => (path.startsWith("/") ? `${API_URL}${path}` : path);

let signingOut = false;

/** Clear the (possibly unverifiable) session cookie, then go to login; a failed logout still redirects. */
async function logoutThenLogin(next: string): Promise<void> {
  if (signingOut) return;
  signingOut = true;
  try {
    await fetch(apiUrl("/api/auth/logout"), { method: "POST", credentials: "include" });
  } catch { /* redirect anyway */ }
  window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}

export async function api<T>(
  path: string,
  opts: { method?: string; json?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const hasBody = opts.json !== undefined;
  const res = await fetch(apiUrl(path), {
    method: opts.method ?? (hasBody ? "POST" : "GET"),
    credentials: "include",
    headers: hasBody ? { "Content-Type": "application/json" } : undefined,
    body: hasBody ? JSON.stringify(opts.json) : undefined,
    signal: opts.signal,
  });
  if (res.status === 401 && typeof window !== "undefined" && !path.startsWith("/api/auth/")) {
    void logoutThenLogin(window.location.pathname);
  }
  if (!res.ok) {
    let msg: unknown = res.statusText;
    try { msg = (await res.json()).detail ?? msg; } catch { /* non-JSON error */ }
    throw new ApiError(res.status, typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}
