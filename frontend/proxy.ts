import { NextRequest, NextResponse } from "next/server";
import { authConfigured, SESSION_COOKIE, validSession } from "./auth";

export function proxy(request: NextRequest) {
  const path = request.nextUrl.pathname;
  const signedIn = validSession(request.cookies.get(SESSION_COOKIE)?.value);
  if (path === "/login") {
    if (signedIn) return NextResponse.redirect(new URL("/", request.url));
    return NextResponse.next();
  }
  if (signedIn) return NextResponse.next();
  if (path.startsWith("/api/")) {
    return NextResponse.json({ detail: authConfigured() ? "Sign in required." : "Access is not configured." }, {
      status: 401, headers: { "cache-control": "no-store" },
    });
  }
  return NextResponse.redirect(new URL("/login", request.url));
}

export const config = { matcher: ["/", "/login", "/api/research", "/api/report", "/api/runs/:path*"] };
