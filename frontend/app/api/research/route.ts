import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 300;

export async function POST(request: NextRequest) {
  const body = await request.text();
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}/research`, {
      method: "POST",
      headers: { "content-type": "application/json", "cache-control": "no-store" },
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(240_000),
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "Research service is unavailable." }, { status: 503, headers: { "cache-control": "no-store" } });
  }
}
