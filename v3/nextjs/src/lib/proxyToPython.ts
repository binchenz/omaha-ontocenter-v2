import { NextRequest, NextResponse } from "next/server";
import { getSessionContext } from "@/lib/session";

// Shared secret with the Python API (see services/pythonApi.ts for the
// companion JSON-body path). Server-only — this file runs in API route
// handlers. Empty → header omitted, Python middleware disabled in dev.
const INTERNAL_SECRET = process.env.INTERNAL_API_SECRET || "";

/**
 * Proxy a multipart/form-data request to the Python API.
 *
 * - Rejects with 401 when the caller is unauthenticated (closes the anonymous
 *   DB-probing surface that existed on `/ingest/discover`).
 * - Forces `tenant_id` from the session — any client-supplied value is dropped
 *   so tenants can't spoof each other.
 * - Forwards the `X-Internal-Auth` shared secret so Python's middleware
 *   accepts the call in production.
 */
export async function proxyMultipartToPython(
  req: NextRequest,
  pythonPath: string,
): Promise<NextResponse> {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const form = await req.formData();
  // Force tenant_id from session — never trust client-provided value.
  form.delete("tenant_id");
  form.append("tenant_id", ctx.tenantId);

  const baseUrl = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";
  const resp = await fetch(`${baseUrl}${pythonPath}`, {
    method: "POST",
    body: form,
    headers: INTERNAL_SECRET ? { "X-Internal-Auth": INTERNAL_SECRET } : {},
  });

  const data = await resp.json().catch(() => ({}));
  return NextResponse.json(data, { status: resp.status });
}
