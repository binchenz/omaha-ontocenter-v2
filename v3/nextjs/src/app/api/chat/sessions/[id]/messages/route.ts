import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSessionContext, ownedSessionWhere } from "@/lib/session";
import { MAX_MESSAGES_PER_SESSION_FETCH } from "@/lib/constants";

function safeParseToolCalls(s: string | null): unknown[] {
  if (!s) return [];
  try {
    const parsed = JSON.parse(s);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    console.warn("[chat/messages] toolCalls JSON parse failed; returning []", e);
    return [];
  }
}

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  // Ownership check + message fetch in parallel — halves latency on session activation.
  const [session, messages] = await Promise.all([
    prisma.chatSession.findFirst({
      where: ownedSessionWhere(ctx, params.id),
      select: { id: true },
    }),
    prisma.chatMessage.findMany({
      where: { sessionId: params.id },
      orderBy: { createdAt: "asc" },
      take: MAX_MESSAGES_PER_SESSION_FETCH,
      select: { id: true, role: true, content: true, toolCalls: true, createdAt: true },
    }),
  ]);

  if (!session) return NextResponse.json({ error: "Not found" }, { status: 404 });

  return NextResponse.json(
    messages.map((m) => ({ ...m, toolCalls: safeParseToolCalls(m.toolCalls) }))
  );
}
