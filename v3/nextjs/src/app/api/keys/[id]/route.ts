import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSessionContext } from "@/lib/session";

export async function DELETE(_req: Request, { params }: { params: { id: string } }) {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const result = await prisma.apiKey.deleteMany({
    where: { id: params.id, userId: ctx.userId, tenantId: ctx.tenantId },
  });
  if (result.count === 0) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return new NextResponse(null, { status: 204 });
}
