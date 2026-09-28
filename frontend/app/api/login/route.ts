import { NextRequest, NextResponse } from "next/server";
import { authConfigured, createSession, credentialsMatch, SESSION_COOKIE, sessionMaxAge } from "../../../auth";

export async function POST(request: NextRequest) {
  if (!authConfigured()) return new NextResponse(null, { status: 303, headers: { location: "/login?error=setup", "cache-control": "no-store" } });
  const form = await request.formData();
  const email = form.get("email");
  const password = form.get("password");
  if (typeof email !== "string" || typeof password !== "string" || !credentialsMatch(email, password)) {
    return new NextResponse(null, { status: 303, headers: { location: "/login?error=invalid", "cache-control": "no-store" } });
  }
  const response = new NextResponse(null, { status: 303, headers: { location: "/", "cache-control": "no-store" } });
  response.cookies.set(SESSION_COOKIE, createSession(), {
    httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", path: "/", maxAge: sessionMaxAge,
  });
  return response;
}
