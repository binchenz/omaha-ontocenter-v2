import { NextResponse } from "next/server";

/**
 * Forward a Python API response back to the Next.js caller, ensuring the
 * client always receives JSON it can parse — even when Python returns a
 * non-JSON 5xx (HTML stack trace, plain text "Internal Server Error", etc.).
 *
 * - JSON content-type → passthrough (no double-stringify).
 * - Anything else → wrapped as { detail: <first 500 chars> } so the browser
 *   gets a usable diagnostic instead of a swallowed empty body.
 */
export async function forwardPythonResponse(resp: Response): Promise<NextResponse> {
  const text = await resp.text();
  const ct = resp.headers.get("content-type") || "";

  if (ct.includes("application/json")) {
    return new NextResponse(text || "{}", {
      status: resp.status,
      headers: { "content-type": "application/json" },
    });
  }

  return NextResponse.json(
    { detail: text.slice(0, 500) || resp.statusText || `HTTP ${resp.status}` },
    { status: resp.status },
  );
}
