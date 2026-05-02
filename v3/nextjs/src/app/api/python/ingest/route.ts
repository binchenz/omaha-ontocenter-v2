import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

const BASE = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  const tenantId = ((session?.user as any)?.tenantId) || "default";

  const formData = await req.formData();
  if (!formData.has("tenant_id")) {
    formData.append("tenant_id", tenantId);
  }

  const res = await fetch(`${BASE}/ingest`, { method: "POST", body: formData });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
