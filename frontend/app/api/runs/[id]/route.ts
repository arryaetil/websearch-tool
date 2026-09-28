import { NextResponse } from "next/server";

type Context = { params: Promise<{ id: string }> };

async function forward(method: "GET" | "DELETE", context: Context) {
  const { id } = await context.params;
  if (!/^[0-9a-f-]{36}$/.test(id)) {
    return NextResponse.json({ detail: "Invalid run ID." }, { status: 400 });
  }
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}/runs/${id}`, {
      method, cache: "no-store",
    });
    return new NextResponse(await response.text(), {
      status: response.status,
      headers: { "content-type": "application/json", "cache-control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "Saved run is unavailable." }, { status: 503 });
  }
}

export async function GET(_request: Request, context: Context) { return forward("GET", context); }
export async function DELETE(_request: Request, context: Context) { return forward("DELETE", context); }
