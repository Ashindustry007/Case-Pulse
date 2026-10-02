import { NextResponse, type NextRequest } from "next/server";
import { roleFromToken, routeDecision } from "@/lib/route-guard";

export function middleware(req: NextRequest) {
  const target = routeDecision(req.nextUrl.pathname, roleFromToken(req.cookies.get("cp_session")?.value));
  return target ? NextResponse.redirect(new URL(target, req.url)) : NextResponse.next();
}

export const config = { matcher: ["/", "/login", "/matters/:path*", "/costs/:path*", "/provider/:path*"] };
