import { NextRequest, NextResponse } from "next/server";

const BASE = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const res = await fetch(`${BASE}/ingest/discover`, { method: "POST", body: formData });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
