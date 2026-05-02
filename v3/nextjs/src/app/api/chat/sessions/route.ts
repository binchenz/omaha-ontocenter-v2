import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

const DEFAULT_TENANT_ID = "default";
const DEFAULT_USER_ID = "demo";

/**
 * Ensures the demo tenant + user rows exist so ChatSession FKs resolve in dev.
 * Cheap upserts — Prisma uses where-by-unique then no-ops on update.
 * TODO(P6): replace with real auth-bound user lookup.
 */
async function ensureDemoIdentity(tenantId: string, userId: string, email?: string | null) {
  await prisma.tenant.upsert({
    where: { id: tenantId },
    update: {},
    create: { id: tenantId, name: "Default", slug: tenantId },
  });
  await prisma.user.upsert({
    where: { id: userId },
    update: {},
    create: {
      id: userId,
      tenantId,
      email: email || `${userId}@local.dev`,
      passwordHash: "",
      name: "Demo User",
    },
  });
}

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user) return NextResponse.json([], { status: 401 });

  const userId = (session.user as any).id || DEFAULT_USER_ID;
  const tenantId = (session.user as any).tenantId || DEFAULT_TENANT_ID;

  const sessions = await prisma.chatSession.findMany({
    where: { userId, tenantId },
    orderBy: { createdAt: "desc" },
    take: 50,
    select: { id: true, title: true, createdAt: true },
  });

  return NextResponse.json(sessions);
}

export async function POST(_req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userId = (session.user as any).id || DEFAULT_USER_ID;
  const tenantId = (session.user as any).tenantId || DEFAULT_TENANT_ID;

  await ensureDemoIdentity(tenantId, userId, session.user.email);

  const chatSession = await prisma.chatSession.create({
    data: {
      userId,
      tenantId,
      title: "新对话",
    },
    select: { id: true, title: true, createdAt: true },
  });

  return NextResponse.json(chatSession);
}
