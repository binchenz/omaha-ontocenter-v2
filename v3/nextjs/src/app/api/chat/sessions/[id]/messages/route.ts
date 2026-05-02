import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSessionContext, ownedSessionWhere } from "@/lib/session";
import {
  MAX_MESSAGES_PER_SESSION_FETCH,
  UPLOAD_MARKER,
  UPLOAD_MARKER_RE,
} from "@/lib/constants";

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

// User messages are persisted with the LLM-facing `[文件已上传] ...` marker
// appended so subsequent turns can detect post-upload context (see
// send/route.ts sticky-ingest). Strip it here so the UI shows the clean
// original text.
//
// Substring fast-path: regex on every row of up to MAX_MESSAGES_PER_SESSION_FETCH
// (=500) is wasted work since ≤1 user message per session ever carries the
// marker. `includes()` is a cheap O(n) Boyer-Moore-ish scan that lets the
// expensive regex run only on the (rare) marker-bearing row.
function stripUserContextMarker(role: string, content: string): string {
  return role === "user" && content.includes(UPLOAD_MARKER)
    ? content.replace(UPLOAD_MARKER_RE, "")
    : content;
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
    messages.map((m) => ({
      ...m,
      content: stripUserContextMarker(m.role, m.content),
      toolCalls: safeParseToolCalls(m.toolCalls),
    }))
  );
}

