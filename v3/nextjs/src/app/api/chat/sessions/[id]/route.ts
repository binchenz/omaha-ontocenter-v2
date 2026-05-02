import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSessionContext, ownedSessionWhere } from "@/lib/session";

export async function DELETE(_req: Request, { params }: { params: { id: string } }) {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  // Tenant-scoped delete. Cascade on chat_messages.session_id removes child rows.
  const result = await prisma.chatSession.deleteMany({
    where: ownedSessionWhere(ctx, params.id),
  });
  if (result.count === 0) return NextResponse.json({ error: "Not found" }, { status: 404 });

  return new NextResponse(null, { status: 204 });
}
