/** UX-only routing by role. The backend is the authority; this just avoids showing the wrong app. */
export type GuardRole = "attorney" | "provider";
export const HOME: Record<GuardRole, string> = { attorney: "/matters", provider: "/provider/cases" };

export function roleFromToken(token?: string): GuardRole | null {
  const part = token?.split(".")[1];
  if (!part) return null;
  try {
    const b64 = part.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(part.length / 4) * 4, "=");
    const claims = JSON.parse(atob(b64));
    if (claims.exp && claims.exp * 1000 < Date.now()) return null;
    return claims.role === "attorney" || claims.role === "provider" ? claims.role : null;
  } catch {
    return null;
  }
}

export function routeDecision(pathname: string, role: GuardRole | null): string | null {
  const attorneyArea = pathname.startsWith("/matters") || pathname.startsWith("/costs");
  const providerArea = pathname.startsWith("/provider");
  const entry = pathname === "/" || pathname === "/login";
  if (!role) {
    if (pathname === "/") return "/login";
    return attorneyArea || providerArea ? `/login?next=${encodeURIComponent(pathname)}` : null;
  }
  if (entry || (role === "provider" && attorneyArea) || (role === "attorney" && providerArea)) return HOME[role];
  return null;
}
