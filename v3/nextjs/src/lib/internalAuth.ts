/** Shared secret + header name for Next.js ↔ Python API traffic.
 *  Set INTERNAL_API_SECRET in both .env files; leave empty only in dev.
 *
 *  SECURITY: this module must not be imported by client components.
 *  `process.env.INTERNAL_API_SECRET` is server-only; if a client component
 *  pulls this in, the header is silently omitted at runtime and Python
 *  rejects with 401 — fails closed (annoying but safe). All consumers today
 *  live inside `app/api/**` route handlers and `app/agent/**` server code.
 */
export const INTERNAL_AUTH_HEADER = "X-Internal-Auth";
export const INTERNAL_SECRET = process.env.INTERNAL_API_SECRET || "";

/** Returns `{ "X-Internal-Auth": secret }` when configured, else `{}` so
 *  object-spread callers stay header-clean in dev. */
export function internalAuthHeaders(): Record<string, string> {
  return INTERNAL_SECRET ? { [INTERNAL_AUTH_HEADER]: INTERNAL_SECRET } : {};
}
