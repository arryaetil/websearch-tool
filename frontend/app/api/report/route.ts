import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}/report.pdf`, {
      method: "POST",
      headers: { "content-type": "application/json", "cache-control": "no-store" },
      body: await request.text(),
      cache: "no-store",
    });
    if (!response.ok) return NextResponse.json({ detail: "Could not create PDF." }, { status: 502, headers: { "cache-control": "no-store" } });
    return new NextResponse(await response.arrayBuffer(), {
      headers: {
        "content-type": "application/pdf",
        "content-disposition": 'attachment; filename="person-research-draft.pdf"',
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Research service is unavailable." }, { status: 503, headers: { "cache-control": "no-store" } });
  }
}
