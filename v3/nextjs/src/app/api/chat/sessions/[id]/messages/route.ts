import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSessionContext } from "@/lib/session";

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  // Verify the session belongs to this user (tenant scoped)
  const session = await prisma.chatSession.findFirst({
    where: { id: params.id, userId: ctx.userId, tenantId: ctx.tenantId },
    select: { id: true },
  });
  if (!session) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const messages = await prisma.chatMessage.findMany({
    where: { sessionId: params.id },
    orderBy: { createdAt: "asc" },
    select: { id: true, role: true, content: true, toolCalls: true, createdAt: true },
  });

  // Parse toolCalls JSON for UI consumption
  return NextResponse.json(
    messages.map((m) => ({
      ...m,
      toolCalls: m.toolCalls ? JSON.parse(m.toolCalls) : [],
    }))
  );
}
