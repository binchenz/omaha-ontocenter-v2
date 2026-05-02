import { prisma } from "@/lib/prisma";
import { hashApiKey } from "@/lib/apiKey";
import type { SessionContext } from "@/lib/session";

export async function getBearerContext(req: Request): Promise<SessionContext | null> {
  const auth = req.headers.get("authorization") || "";
  const m = auth.match(/^Bearer\s+(.+)$/i);
  if (!m) return null;

  const hash = hashApiKey(m[1]);
  const key = await prisma.apiKey.findUnique({
    where: { keyHash: hash },
    select: { userId: true, tenantId: true, scopes: true, expiresAt: true, user: { select: { email: true } } },
  });
  if (!key) return null;
  if (key.expiresAt && key.expiresAt <= new Date()) return null;

  return {
    userId: key.userId,
    tenantId: key.tenantId,
    email: key.user?.email ?? null,
    scopes: key.scopes.split(",").map((s) => s.trim()).filter(Boolean),
  };
}
