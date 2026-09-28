import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE } from "../../../auth";

export async function POST(request: NextRequest) {
  const response = new NextResponse(null, { status: 303, headers: { location: "/login", "cache-control": "no-store" } });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
