import { NextResponse } from "next/server";

const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

async function forward(method: "GET" | "DELETE") {
  try {
    const response = await fetch(`${backend}/runs`, { method, cache: "no-store" });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "Saved runs are unavailable." }, { status: 503 });
  }
}

export async function GET() { return forward("GET"); }
export async function DELETE() { return forward("DELETE"); }
