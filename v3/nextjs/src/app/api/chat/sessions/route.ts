import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { ensureDemoIdentity, getSessionContext } from "@/lib/session";
import { DEFAULT_SESSION_TITLE } from "@/lib/constants";

export async function GET() {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json([], { status: 401 });

  const sessions = await prisma.chatSession.findMany({
    where: { userId: ctx.userId, tenantId: ctx.tenantId },
    orderBy: { createdAt: "desc" },
    take: 50,
    select: { id: true, title: true, createdAt: true },
  });

  return NextResponse.json(sessions);
}

export async function POST() {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  await ensureDemoIdentity(ctx);

  const chatSession = await prisma.chatSession.create({
    data: { userId: ctx.userId, tenantId: ctx.tenantId, title: DEFAULT_SESSION_TITLE },
    select: { id: true, title: true, createdAt: true },
  });

  return NextResponse.json(chatSession);
}
