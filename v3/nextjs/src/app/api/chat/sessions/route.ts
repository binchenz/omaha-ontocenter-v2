import { NextRequest, NextResponse } from "next/server";

const sessions = new Map<string, any>();

export async function GET() {
  return NextResponse.json([...sessions.values()]);
}

export async function POST(req: NextRequest) {
  const id = Math.random().toString(36).slice(2, 10);
  const session = { id, title: "新对话", ontologyIds: [], plan: null, createdAt: new Date().toISOString() };
  sessions.set(id, session);
  return NextResponse.json(session);
}
