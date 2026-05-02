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

/**
 * Scope predicate for querying/mutating a chat session owned by the current
 * user in the current tenant. Centralises the owner-scoped `where` clause
 * so route handlers can't accidentally omit `tenantId` and leak cross-tenant.
 */
export function ownedSessionWhere(ctx: SessionContext, sessionId?: string) {
  const base = { userId: ctx.userId, tenantId: ctx.tenantId };
  return sessionId ? { ...base, id: sessionId } : base;
}

const _demoReady = new Map<string, Promise<void>>();

/**
 * Idempotently ensure the demo tenant+user exist so ChatSession FKs resolve.
 * Dev-only. Cached per-userId so the first-login promise can't shadow a
 * different user's upsert (which previously left B with no row → FK violation
 * on B's first ChatSession insert).
 * Replaced by real auth-bound user lookup in P6.
 */
export async function ensureDemoIdentity(ctx: SessionContext): Promise<void> {
  if (process.env.NODE_ENV === "production") return;
  const cached = _demoReady.get(ctx.userId);
  if (cached) return cached;
  const promise = (async () => {
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
  _demoReady.set(ctx.userId, promise);
  return promise;
}
