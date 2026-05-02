import { NextRequest, NextResponse } from "next/server";
import { getSessionContext } from "@/lib/session";
import { internalAuthHeaders } from "@/lib/internalAuth";

const BASE_URL = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";

/**
 * Server-side proxy for client components that need to talk to the Python API.
 *
 * Why: when INTERNAL_API_SECRET is set, the Python API requires X-Internal-Auth
 * which only exists on the Next.js server (NEXT_PUBLIC_-prefix would leak it).
 * Client components route through here; we authenticate the user via session,
 * inject tenant_id, then forward to Python with the shared secret.
 *
 * Tenant safety: `tenant_id` is ALWAYS overwritten with the session's tenant —
 * a client cannot spoof another tenant by passing `?tenant_id=imposter`.
 */
async function proxy(
  req: NextRequest,
  { params }: { params: { path: string[] } },
) {
  const ctx = await getSessionContext();
  if (!ctx) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const subpath = params.path.join("/");
  const url = new URL(`${BASE_URL}/${subpath}`);

  // Forward query params from the client request, BUT force tenant_id from session.
  for (const [k, v] of req.nextUrl.searchParams.entries()) {
    if (k === "tenant_id") continue; // never trust client-provided tenant
    url.searchParams.set(k, v);
  }
  url.searchParams.set("tenant_id", ctx.tenantId);

  // Build forwarded headers — shared secret first, then content-type passthrough.
  // We deliberately drop cookies / host / hop-by-hop headers; the Python API
  // trusts the shared secret, not the browser session.
  const headers: Record<string, string> = { ...internalAuthHeaders() };
  const ct = req.headers.get("content-type");
  if (ct) headers["content-type"] = ct;

  let body: BodyInit | undefined = undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    // arrayBuffer() handles JSON, multipart, and other binary payloads uniformly.
    body = await req.arrayBuffer();
  }

  const resp = await fetch(url.toString(), {
    method: req.method,
    headers,
    body,
  });

  // Forward response — try JSON passthrough, fall back to wrapped text so the
  // client always gets JSON it can parse (non-JSON 5xx HTML traces, etc.).
  const text = await resp.text();
  const respCt = resp.headers.get("content-type") || "";
  const init = {
    status: resp.status,
    headers: { "content-type": respCt || "application/json" },
  };

  if (respCt.includes("application/json")) {
    return new NextResponse(text, init);
  }
  return NextResponse.json(
    { detail: text.slice(0, 500) || resp.statusText },
    { status: resp.status },
  );
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const DELETE = proxy;
export const PATCH = proxy;
