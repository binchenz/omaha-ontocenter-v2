# A1: Agent Loop 统一到 JS — Python 仅做数据层

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

## Goal

把 v3 的 MCP server 从 Python 搬到 Next.js，复用现有 `tool-registry.ts` 作为唯一工具源。删除 Python 端 `services/mcp/` + `api/mcp.py` + `api/mcp_runtime.py` 及相关测试。Python 收敛为纯数据层。

**Why:** 当前两套并行抽象（JS `tool-registry.ts` + Python `tool_generator.py`）造成工具描述 drift（已发现：Python 有 `count_*`，JS 之前缺；step 1 已对齐）。两套语言两套相似抽象的维护成本是真技术债。

**Non-goals:**
- 不重写现有 chat agent loop（react.ts streamText 不动）
- 不实现 OAuth2（用 API key 鉴权，已有 ApiKey 表）
- 不做 MCP "skills" 概念（Python 那边的 skill_packager 是 the assistant 风格 skill 打包，与 v3 chat 用的 SKILL.md 是不同的东西，直接删）

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Next.js (单进程)                                         │
│                                                          │
│  ┌──────────────┐       ┌────────────────────────┐     │
│  │ /chat (boss) │       │ /api/mcp (third-party) │     │
│  │   ↓          │       │   ↓                    │     │
│  │ skill-router │       │ Bearer ocv3_xxx → key  │     │
│  │   ↓          │       │   ↓                    │     │
│  │ react.ts     │       │ JSON-RPC dispatcher    │     │
│  └──────┬───────┘       └─────┬──────────────────┘     │
│         │                     │                         │
│         └────┬────────────────┘                         │
│              ↓                                          │
│         tool-registry.ts (single source of truth)       │
│              ↓                                          │
│         pythonApi.ts → /ontology/{id}/query             │
└─────────────────────────────────────────────────────────┘
                       ↓
              ┌────────────────────┐
              │ Python (data层)    │
              │ /ingest /ontology  │
              │ /datasources       │
              │ NO MCP / NO LLM    │
              └────────────────────┘
```

## File Map

```
NEW    v3/nextjs/src/lib/apiKey.ts                              — hash, generate, verify
NEW    v3/nextjs/src/app/api/keys/route.ts                      — list + create
NEW    v3/nextjs/src/app/api/keys/[id]/route.ts                 — delete
NEW    v3/nextjs/src/app/api/mcp/route.ts                       — JSON-RPC handler
NEW    v3/nextjs/src/app/agent/mcp-adapter.ts                   — Tool[] → MCP tools/list, dispatch tools/call
NEW    v3/nextjs/src/lib/bearerAuth.ts                          — Bearer token → ApiKey row → SessionContext

MODIFY v3/nextjs/src/app/(app)/settings/api-keys/page.tsx        — wire to real backend (currently mock)
MODIFY v3/nextjs/src/app/agent/tool-registry.ts                  — buildIngestTools(): allow disabling create_ontology for MCP scope

DELETE v3/python-api/app/api/mcp.py
DELETE v3/python-api/app/api/mcp_runtime.py
DELETE v3/python-api/app/services/mcp/                           — entire dir
DELETE v3/python-api/app/models/mcp.py                           — if unreferenced after the above

MODIFY v3/python-api/app/main.py                                 — drop mcp router includes
MODIFY v3/python-api/tests/test_e2e.py                           — drop MCP-related tests; keep ontology/ingest/datasources
```

## Tasks

---

### Task 1: API key generate + verify primitives

**Files:**
- Create: `v3/nextjs/src/lib/apiKey.ts`

- [ ] **Step 1.1: Implement hash + verify**

`apiKey.ts`:

```typescript
import { createHash, randomBytes } from "crypto";

const KEY_PREFIX = "ocv3_";

/** Generate a random API key. The plaintext is shown to the user ONCE. */
export function generateApiKey(): { plaintext: string; hash: string } {
  const random = randomBytes(24).toString("base64url");
  const plaintext = `${KEY_PREFIX}${random}`;
  return { plaintext, hash: hashApiKey(plaintext) };
}

/** SHA-256 hex hash. Stored in DB; we never store plaintext. */
export function hashApiKey(plaintext: string): string {
  return createHash("sha256").update(plaintext).digest("hex");
}

/** Last 4 chars of plaintext suffix shown after creation for display. */
export function keyDisplaySuffix(plaintext: string): string {
  return plaintext.slice(-4);
}
```

- [ ] **Step 1.2: Commit**

```bash
git -C /Users/wangfushuaiqi/omaha_ontocenter add v3/nextjs/src/lib/apiKey.ts
git -C /Users/wangfushuaiqi/omaha_ontocenter commit -m "feat(api-keys): hash/generate/suffix primitives"
```

---

### Task 2: Bearer auth helper

**Files:**
- Create: `v3/nextjs/src/lib/bearerAuth.ts`

- [ ] **Step 2.1: Implement Bearer → SessionContext**

```typescript
import { prisma } from "@/lib/prisma";
import { hashApiKey } from "@/lib/apiKey";
import type { SessionContext } from "@/lib/session";

/**
 * Resolve a Bearer-token request to a SessionContext.
 * Returns null on missing/invalid token.
 */
export async function getBearerContext(req: Request): Promise<SessionContext | null> {
  const auth = req.headers.get("authorization") || "";
  const m = auth.match(/^Bearer\s+(.+)$/i);
  if (!m) return null;

  const hash = hashApiKey(m[1]);
  const key = await prisma.apiKey.findFirst({
    where: {
      keyHash: hash,
      OR: [{ expiresAt: null }, { expiresAt: { gt: new Date() } }],
    },
    select: { userId: true, tenantId: true, scopes: true, user: { select: { email: true } } },
  });
  if (!key) return null;

  return {
    userId: key.userId,
    tenantId: key.tenantId,
    email: key.user?.email ?? null,
    scopes: key.scopes.split(",").map((s) => s.trim()).filter(Boolean),
  };
}
```

- [ ] **Step 2.2: Extend SessionContext type**

Edit `v3/nextjs/src/lib/session.ts` — add optional `scopes?: string[]` to `SessionContext`. Browser-session paths leave it undefined; bearer-token paths populate it.

- [ ] **Step 2.3: Commit**

```bash
git -C /Users/wangfushuaiqi/omaha_ontocenter add v3/nextjs/src/lib/bearerAuth.ts v3/nextjs/src/lib/session.ts
git -C /Users/wangfushuaiqi/omaha_ontocenter commit -m "feat(api-keys): Bearer token → SessionContext resolver"
```

---

### Task 3: API key CRUD endpoints

**Files:**
- Create: `v3/nextjs/src/app/api/keys/route.ts`
- Create: `v3/nextjs/src/app/api/keys/[id]/route.ts`

- [ ] **Step 3.1: List + create**

`/api/keys/route.ts`:

```typescript
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
  const label = (body.label || "未命名").slice(0, 64);
  const scopes = body.scopes || "mcp:read";

  const { plaintext, hash } = generateApiKey();
  const key = await prisma.apiKey.create({
    data: { tenantId: ctx.tenantId, userId: ctx.userId, keyHash: hash, label, scopes },
    select: { id: true, label: true, scopes: true, createdAt: true },
  });
  // Return plaintext ONCE.
  return NextResponse.json({ ...key, plaintext, suffix: keyDisplaySuffix(plaintext) });
}
```

- [ ] **Step 3.2: Delete**

`/api/keys/[id]/route.ts`:

```typescript
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
```

- [ ] **Step 3.3: Verify + commit**

```bash
npm --prefix v3/nextjs run typecheck
git add v3/nextjs/src/app/api/keys/
git commit -m "feat(api-keys): CRUD endpoints (list/create with one-shot plaintext, delete)"
```

---

### Task 4: Wire settings/api-keys/page.tsx to real backend

**Files:**
- Modify: `v3/nextjs/src/app/(app)/settings/api-keys/page.tsx`

- [ ] **Step 4.1: Replace mock with fetch calls**

Read existing page; rip out the mock state. Hook to:
- `useEffect` → `GET /api/keys` 填列表
- "生成新密钥" 按钮 → `POST /api/keys` with `{ label }`，把返回的 `plaintext` 一次性显示在大框里
- "删除" 按钮 → `DELETE /api/keys/{id}`

UI requirements:
- Each key row shows: label, scopes, createdAt, expiresAt (or "永久"), 删除按钮
- After create, big yellow box "**仅此一次显示**" with copy button + warning
- Refresh shows only label + suffix (no plaintext)

- [ ] **Step 4.2: Commit**

```bash
git add v3/nextjs/src/app/\(app\)/settings/api-keys/page.tsx
git commit -m "feat(api-keys): wire settings UI to real backend"
```

---

### Task 5: MCP JSON-RPC adapter

**Files:**
- Create: `v3/nextjs/src/app/agent/mcp-adapter.ts`

- [ ] **Step 5.1: Tool → MCP shape**

```typescript
import { z } from "zod";
import type { Tool } from "./tool-registry";

/** Convert a Tool to MCP tools/list entry — name + description + JSON Schema input. */
export function toolToMcpDescriptor(name: string, tool: Tool) {
  return {
    name,
    description: tool.description,
    inputSchema: schemaForToolName(name),
  };
}

/** JSON Schema (NOT zod) for each tool family. Mirrors react.ts:schemaForTool. */
function schemaForToolName(name: string): object {
  if (name.startsWith("search_")) {
    return {
      type: "object",
      properties: {
        filters: { type: "object", description: "按列过滤" },
        limit: { type: "integer", description: "返回数量上限", default: 10 },
      },
    };
  }
  if (name.startsWith("aggregate_")) {
    return {
      type: "object",
      properties: {
        measures: { type: "array", items: { type: "string" }, description: "聚合表达式" },
        group_by: { type: "array", items: { type: "string" } },
        filters: { type: "object" },
      },
      required: ["measures"],
    };
  }
  if (name.startsWith("count_")) {
    return { type: "object", properties: { filters: { type: "object" } } };
  }
  return { type: "object", additionalProperties: true };
}
```

- [ ] **Step 5.2: Commit**

```bash
git add v3/nextjs/src/app/agent/mcp-adapter.ts
git commit -m "feat(mcp): Tool → JSON Schema adapter for tools/list response"
```

---

### Task 6: MCP route — JSON-RPC dispatcher

**Files:**
- Create: `v3/nextjs/src/app/api/mcp/route.ts`

- [ ] **Step 6.1: Implement initialize/tools/list/tools/call**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { getBearerContext } from "@/lib/bearerAuth";
import { ontologyApi } from "@/services/pythonApi";
import { loadAllTools } from "@/app/agent/tool-registry";
import { toolToMcpDescriptor } from "@/app/agent/mcp-adapter";
import type { OntologySchema } from "@/types/api";

export async function POST(req: NextRequest) {
  // MCP: JSON-RPC 2.0 with method, params, id.
  const body = await req.json().catch(() => null);
  if (!body || body.jsonrpc !== "2.0") {
    return NextResponse.json(
      { jsonrpc: "2.0", id: null, error: { code: -32600, message: "Invalid Request" } },
      { status: 400 },
    );
  }

  const ctx = await getBearerContext(req);
  if (!ctx) {
    return NextResponse.json(
      { jsonrpc: "2.0", id: body.id, error: { code: -32001, message: "Unauthorized" } },
      { status: 401 },
    );
  }

  try {
    const result = await dispatch(body.method, body.params || {}, ctx);
    return NextResponse.json({ jsonrpc: "2.0", id: body.id, result });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { jsonrpc: "2.0", id: body.id, error: { code: -32000, message: msg } },
    );
  }
}

async function dispatch(method: string, params: any, ctx: SessionContext) {
  if (method === "initialize") {
    return {
      protocolVersion: "2024-11-05",
      capabilities: { tools: {} },
      serverInfo: { name: "ontocenter-v3", version: "0.1.0" },
    };
  }

  if (method === "tools/list") {
    const schemas: OntologySchema[] = await ontologyApi.listSchemas(ctx.tenantId, { limit: 500 });
    const tools = loadAllTools(schemas, ctx.tenantId);
    return {
      tools: Object.entries(tools).map(([name, t]) => toolToMcpDescriptor(name, t)),
    };
  }

  if (method === "tools/call") {
    const { name, arguments: args } = params;
    const schemas: OntologySchema[] = await ontologyApi.listSchemas(ctx.tenantId, { limit: 500 });
    const tools = loadAllTools(schemas, ctx.tenantId);
    const tool = tools[name];
    if (!tool) throw new Error(`Unknown tool: ${name}`);
    const result = await tool.execute(args || {});
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  }

  throw new Error(`Method not found: ${method}`);
}
```

- [ ] **Step 6.2: Smoke test with curl**

```bash
# Generate a key first via UI or:
KEY=$(curl -sb /tmp/cookies.txt -X POST http://127.0.0.1:3000/api/keys -H "Content-Type: application/json" -d '{"label":"smoke","scopes":"mcp:read"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['plaintext'])")

# Test initialize
curl -s -X POST http://127.0.0.1:3000/api/mcp \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize"}'

# Test tools/list
curl -s -X POST http://127.0.0.1:3000/api/mcp \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | python3 -m json.tool

# Test tools/call (count)
curl -s -X POST http://127.0.0.1:3000/api/mcp \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"count_<slug>","arguments":{}}}'
```

- [ ] **Step 6.3: Commit**

```bash
git add v3/nextjs/src/app/api/mcp/route.ts
git commit -m "feat(mcp): JSON-RPC handler — initialize, tools/list, tools/call via Bearer auth

Replaces Python /mcp/{slug} runtime. Uses tool-registry.ts as the single
source of truth for tool descriptions; loadAllTools() runs once per request
(future opt: cache by tenant+ontology version)."
```

---

### Task 7: Delete Python MCP code

**Files:**
- Delete: `v3/python-api/app/api/mcp.py`
- Delete: `v3/python-api/app/api/mcp_runtime.py`
- Delete: `v3/python-api/app/services/mcp/` (entire dir)
- Maybe-delete: `v3/python-api/app/models/mcp.py` (verify no references)
- Modify: `v3/python-api/app/main.py` (drop router includes)
- Modify: `v3/python-api/tests/test_e2e.py` (drop MCP tests)

- [ ] **Step 7.1: Audit references**

```bash
grep -rn "from app.api.mcp\|from app.services.mcp\|api.mcp_runtime" /Users/wangfushuaiqi/omaha_ontocenter/v3/python-api/app /Users/wangfushuaiqi/omaha_ontocenter/v3/python-api/tests
```

Expect: hits in `main.py` and `test_e2e.py`. Anywhere else → investigate.

- [ ] **Step 7.2: Drop main.py router includes**

Read `v3/python-api/app/main.py`, find lines like:
```python
from app.api import mcp, mcp_runtime
app.include_router(mcp.router)
app.include_router(mcp_runtime.router)
```
Remove both.

- [ ] **Step 7.3: Drop tests**

Read `v3/python-api/tests/test_e2e.py` for tests referring to `/mcp`, e.g. `test_07_*`, `test_11_mcp_runtime_endpoint`, etc. Drop them.

- [ ] **Step 7.4: rm files**

```bash
rm /Users/wangfushuaiqi/omaha_ontocenter/v3/python-api/app/api/mcp.py
rm /Users/wangfushuaiqi/omaha_ontocenter/v3/python-api/app/api/mcp_runtime.py
rm -r /Users/wangfushuaiqi/omaha_ontocenter/v3/python-api/app/services/mcp/
```

For `models/mcp.py`:
```bash
grep -rn "from app.models.mcp" /Users/wangfushuaiqi/omaha_ontocenter/v3/python-api
```
If 0 hits and `models/__init__.py` doesn't re-export, delete. If imports remain, keep + flag.

- [ ] **Step 7.5: Verify Python tests still pass**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/v3/python-api && PYTHONPATH=. .venv/bin/pytest tests/ -q
```

Expect: ≥40 passing (43 minus the dropped MCP tests). Should be 40-41.

- [ ] **Step 7.6: Commit**

```bash
git -C /Users/wangfushuaiqi/omaha_ontocenter add v3/python-api/
git -C /Users/wangfushuaiqi/omaha_ontocenter commit -m "refactor(python): delete MCP server — moved to Next.js (A1)

Net deletion: ~600 lines across api/mcp.py, api/mcp_runtime.py,
services/mcp/. Tests for /mcp/{slug} dropped — equivalent coverage now
lives in Next.js MCP route (smoke tested via curl in Task 6).

Python's role narrows to: ingest, ontology CRUD, OAG query, datasources.
No more LLM-related code on the Python side."
```

---

### Task 8: End-to-end smoke + final verify

- [ ] **Step 8.1: Stack startup**

```bash
cd v3/python-api && nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 &
npm --prefix v3/nextjs run dev &
sleep 10
```

- [ ] **Step 8.2: chat path still works**

Login via curl (the standard E2E#5 dance), upload a CSV, confirm, query.
Expect: identical UX to before A1 — chat agent untouched.

- [ ] **Step 8.3: MCP path works**

Generate API key via UI (or POST /api/keys). Use it via curl to call `tools/list` and `tools/call`. 

(Optional: connect the assistant Desktop to `http://127.0.0.1:3000/api/mcp` with the key in Authorization. Check tools appear and execute.)

- [ ] **Step 8.4: Final state check**

```bash
git -C /Users/wangfushuaiqi/omaha_ontocenter log --oneline | head -10
npm --prefix v3/nextjs run typecheck
npm --prefix v3/nextjs run build
cd v3/python-api && PYTHONPATH=. .venv/bin/pytest tests/ -q
```

All clean.

---

## Risk register

- **R1: MCP dispatch performance**: every `tools/list` / `tools/call` re-fetches all schemas. For now acceptable (typical client polls list once at connect). Future opt: process-level cache keyed on (tenantId, ontology updatedAt max).
- **R2: API key enumeration**: SHA-256 hash lookup uses Prisma `findFirst` with full-table scan (no index on keyHash). For 1000s of keys, slow. Mitigation: add `@@index([keyHash])` if N>500. Out of scope for v1.
- **R3: Settings UI gap**: existing UI is mock; new page may need polish (label edit, expires-at picker). Acceptable for first cut.
- **R4: Python tests assume MCP**: dropping tests reduces coverage. Mitigation: replacement test in `v3/nextjs` (could add a vitest later — not in this plan).

## Out of scope (explicitly)

- OAuth2 (use API key)
- MCP "skills" packaging (Python's was a different concept; v3 SKILL.md stays)
- Streaming MCP responses (current spec uses one-shot JSON-RPC)
- Cron-driven background agents (motivation for keeping loop in Python; not pursuing)
- Replacing chat agent (loop stays in JS via Vercel SDK)
