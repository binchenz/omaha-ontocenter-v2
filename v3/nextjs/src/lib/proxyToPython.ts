import { NextRequest, NextResponse } from "next/server";
import { getSessionContext } from "@/lib/session";
import { internalAuthHeaders } from "@/lib/internalAuth";

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
    headers: internalAuthHeaders(),
  });

  const text = await resp.text();
  let data: unknown;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    // Non-JSON response (e.g. HTML stack trace from a Python 500 or plain-text
    // "Internal Server Error"). Wrap it so the client gets a useful diagnostic
    // instead of an empty `{}` body. Cap at 500 chars to avoid echoing a full
    // stack trace back to the browser.
    data = { detail: text.slice(0, 500) || resp.statusText || `HTTP ${resp.status}` };
  }
  return NextResponse.json(data, { status: resp.status });
}
