import { getServerSession } from "next-auth";
import { authOptions } from "./auth";
import { prisma } from "./prisma";
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "./constants";

export interface SessionContext {
  userId: string;
  tenantId: string;
  email: string | null;
}

/** Resolve authenticated session context, or null if unauthenticated. */
export async function getSessionContext(): Promise<SessionContext | null> {
  const s = await getServerSession(authOptions);
  if (!s?.user) return null;
  return {
    userId: s.user.id || DEFAULT_USER_ID,
    tenantId: s.user.tenantId || DEFAULT_TENANT_ID,
    email: s.user.email ?? null,
  };
}

let _demoReady: Promise<void> | null = null;

/**
 * Idempotently ensure the demo tenant+user exist so ChatSession FKs resolve.
 * Dev-only. Cached per-process so repeated logins don't re-upsert.
 * Replaced by real auth-bound user lookup in P6.
 */
export async function ensureDemoIdentity(ctx: SessionContext): Promise<void> {
  if (process.env.NODE_ENV === "production") return;
  if (_demoReady) return _demoReady;
  _demoReady = (async () => {
    await prisma.tenant.upsert({
      where: { id: ctx.tenantId },
      update: {},
      create: { id: ctx.tenantId, name: "Default", slug: ctx.tenantId },
    });
    await prisma.user.upsert({
      where: { id: ctx.userId },
      update: {},
      create: {
        id: ctx.userId,
        tenantId: ctx.tenantId,
        email: ctx.email || `${ctx.userId}@local.dev`,
        passwordHash: "",
        name: "Demo User",
      },
    });
  })();
  return _demoReady;
}
