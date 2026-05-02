import { NextRequest } from "next/server";
import { proxyMultipartToPython } from "@/app/api/proxy/_lib/proxyToPython";

export const POST = (req: NextRequest) => proxyMultipartToPython(req, "/ingest/discover");
