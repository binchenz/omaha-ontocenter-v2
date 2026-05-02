import { NextRequest } from "next/server";
import { proxyMultipartToPython } from "@/lib/proxyToPython";

export const POST = (req: NextRequest) => proxyMultipartToPython(req, "/ingest/discover");
