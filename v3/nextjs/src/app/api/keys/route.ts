import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { getSessionContext } from "@/lib/session";
import { generateApiKey, keyDisplaySuffix } from "@/lib/apiKey";

export async function GET() {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const keys = await prisma.apiKey.findMany({
    where: { userId: ctx.userId, tenantId: ctx.tenantId },
    orderBy: { createdAt: "desc" },
    select: { id: true, label: true, scopes: true, createdAt: true, expiresAt: true },
  });
  return NextResponse.json(keys);
}

export async function POST(req: NextRequest) {
  const ctx = await getSessionContext();
  if (!ctx) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const label = String(body.label || "未命名").slice(0, 64);
  const scopes = String(body.scopes || "mcp:read");

  const { plaintext, hash } = generateApiKey();
  const key = await prisma.apiKey.create({
    data: { tenantId: ctx.tenantId, userId: ctx.userId, keyHash: hash, label, scopes },
    select: { id: true, label: true, scopes: true, createdAt: true },
  });
  return NextResponse.json({ ...key, plaintext, suffix: keyDisplaySuffix(plaintext) });
}
