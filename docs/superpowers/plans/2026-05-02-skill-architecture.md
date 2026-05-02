# V3 Skill Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace v3's planner-based Agent with a Claude Code-style Skill system so users can upload files and query data entirely through Chat.

**Architecture:** SKILL.md files define workflows as markdown. A skill-router uses LLM to pick the right skill per message. The skill's instructions are injected into the system prompt, and the existing react.ts executes with tools. Python backend is unchanged.

**Tech Stack:** Next.js 14, Vercel AI SDK, DeepSeek (OpenAI-compatible), TypeScript, gray-matter (frontmatter parsing)

---

## File Map

```
CREATE  v3/nextjs/src/skills/data-ingest/SKILL.md
CREATE  v3/nextjs/src/skills/data-query/SKILL.md
CREATE  v3/nextjs/src/skills/data-explore/SKILL.md
CREATE  v3/nextjs/src/skills/general-chat/SKILL.md
CREATE  v3/nextjs/src/app/agent/skill-router.ts
CREATE  v3/nextjs/src/app/agent/skill-loader.ts
MODIFY  v3/nextjs/src/app/agent/tool-registry.ts      — add 3 new tools
MODIFY  v3/nextjs/src/app/agent/react.ts               — accept skillInstructions instead of plan
REWRITE v3/nextjs/src/app/api/chat/sessions/[id]/send/route.ts
MODIFY  v3/nextjs/src/app/(app)/chat/page.tsx           — file upload + collapsible details
DELETE  v3/nextjs/src/app/agent/planner.ts
```

---

### Task 1: Create 4 SKILL.md files

**Files:**
- Create: `v3/nextjs/src/skills/data-ingest/SKILL.md`
- Create: `v3/nextjs/src/skills/data-query/SKILL.md`
- Create: `v3/nextjs/src/skills/data-explore/SKILL.md`
- Create: `v3/nextjs/src/skills/general-chat/SKILL.md`

- [ ] **Step 1: Create data-ingest skill**

```markdown
---
name: data-ingest
description: 用户上传文件或提到新数据时触发。接收文件→解析schema→用大白话确认→创建本体→注册数据源
triggers:
  - 上传文件（Excel/CSV）
  - "帮我分析这个"
  - "导入数据"
  - "上传"
  - "新数据"
---

# 数据接入助手

你正在帮用户导入一份新的数据文件。按以下步骤执行：

## 步骤

1. 调用 `ingest_file` 工具，传入用户上传的文件信息
2. 拿到 schema 推断结果后，用中文大白话向用户描述每一列：
   - 用"金额(元)"代替 currency
   - 用"日期"代替 date/datetime
   - 用"文字"代替 text
   - 用"分类"代替 enum，并列出前几个值
   - 用"编号"代替 id
   - 用"数字"代替 number
3. 问用户"对吗？"等待确认
4. 用户确认后，调用 `create_ontology` 工具
5. 完成后说"数据已就绪（X 条记录），你想了解什么？"

## 规则

- 绝不展示 YAML、JSON、SQL 或任何代码
- 绝不使用 semantic_type、ontology、schema 等技术术语
- 如果用户说某列理解错了，修正描述后重新调用 create_ontology
- 如果文件解析失败，用大白话解释原因（如"文件格式不对，请上传 Excel 或 CSV"）
```

- [ ] **Step 2: Create data-query skill**

```markdown
---
name: data-query
description: 用户对已有数据提问时触发。查询数据→分析→给出业务洞察
triggers:
  - 提问已有数据
  - "多少""统计""对比""分析""趋势""排名"
  - "哪个""为什么""怎么样"
---

# 数据查询助手

你正在帮用户分析已有的业务数据。

## 步骤

1. 先调用 `list_my_data` 确认有哪些数据可用
2. 根据用户问题选择合适的查询工具（search_* 或 aggregate_*）
3. 用具体数字回答，给出业务洞察
4. 主动建议下一步可以看什么

## 规则

- 数据用具体数字说话，不要说"较多""较少"
- 金额自动加 ¥ 和千分位
- 百分比保留一位小数
- 如果数据不存在，告诉用户"我还没有这方面的数据，能上传相关的文件吗？"
- 不要复述查询过程，直接给结论
```

- [ ] **Step 3: Create data-explore skill**

```markdown
---
name: data-explore
description: 用户想了解有什么数据可用时触发
triggers:
  - "有什么数据"
  - "能分析什么"
  - "我的数据"
  - "数据列表"
---

# 数据浏览助手

用户想知道平台上有哪些数据可以分析。

## 步骤

1. 调用 `list_my_data` 获取所有数据源和本体
2. 用大白话列出每个数据集：名称、有多少条数据、包含哪些信息
3. 建议用户可以问什么问题

## 规则

- 不要说"本体""数据源""ontology"，说"数据集"或"你的XX数据"
- 列出具体能问的示例问题
```

- [ ] **Step 4: Create general-chat skill**

```markdown
---
name: general-chat
description: 闲聊、问候、与数据分析无关的问题
triggers:
  - 问候（你好/hi/hello）
  - 闲聊
  - 与数据无关的问题
---

# 通用对话

用户在闲聊或问与数据无关的问题。

## 规则

- 友好回应，简短
- 适时引导回数据分析："有什么数据需要我帮你看看吗？"
- 不要调用任何工具
```

- [ ] **Step 5: Install gray-matter for frontmatter parsing**

Run: `cd v3/nextjs && npm install gray-matter`

- [ ] **Step 6: Commit**

```bash
git add v3/nextjs/src/skills/ v3/nextjs/package.json v3/nextjs/package-lock.json
git commit -m "feat: add 4 SKILL.md definitions for skill-based agent"
```

---

### Task 2: Skill Loader

**Files:**
- Create: `v3/nextjs/src/app/agent/skill-loader.ts`

- [ ] **Step 1: Implement skill-loader.ts**

```typescript
import fs from "fs";
import path from "path";
import matter from "gray-matter";

export interface SkillFrontmatter {
  name: string;
  description: string;
  triggers: string[];
}

export interface Skill {
  frontmatter: SkillFrontmatter;
  body: string;
  dir: string;
}

const SKILLS_DIR = path.join(process.cwd(), "src", "skills");

let _indexCache: SkillFrontmatter[] | null = null;

export function loadSkillIndex(): SkillFrontmatter[] {
  if (_indexCache) return _indexCache;

  const entries = fs.readdirSync(SKILLS_DIR, { withFileTypes: true });
  const index: SkillFrontmatter[] = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const mdPath = path.join(SKILLS_DIR, entry.name, "SKILL.md");
    if (!fs.existsSync(mdPath)) continue;

    const raw = fs.readFileSync(mdPath, "utf-8");
    const { data } = matter(raw);
    index.push({
      name: data.name || entry.name,
      description: data.description || "",
      triggers: data.triggers || [],
    });
  }

  _indexCache = index;
  return index;
}

export function loadSkillFull(skillName: string): Skill | null {
  const mdPath = path.join(SKILLS_DIR, skillName, "SKILL.md");
  if (!fs.existsSync(mdPath)) return null;

  const raw = fs.readFileSync(mdPath, "utf-8");
  const { data, content } = matter(raw);

  return {
    frontmatter: {
      name: data.name || skillName,
      description: data.description || "",
      triggers: data.triggers || [],
    },
    body: content.trim(),
    dir: path.join(SKILLS_DIR, skillName),
  };
}

export function buildSkillIndexPrompt(): string {
  const skills = loadSkillIndex();
  const lines = skills.map(
    (s) => `- ${s.name}: ${s.description} (触发: ${s.triggers.join(", ")})`
  );
  return `可用技能:\n${lines.join("\n")}`;
}
```

- [ ] **Step 2: Commit**

```bash
git add v3/nextjs/src/app/agent/skill-loader.ts
git commit -m "feat: add skill-loader with frontmatter index + full body loading"
```

---

### Task 3: Skill Router

**Files:**
- Create: `v3/nextjs/src/app/agent/skill-router.ts`

- [ ] **Step 1: Implement skill-router.ts**

```typescript
import { generateObject } from "ai";
import { createOpenAI } from "@ai-sdk/openai";
import { z } from "zod";
import { buildSkillIndexPrompt, loadSkillFull, type Skill } from "./skill-loader";

const llm = createOpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: process.env.OPENAI_BASE_URL,
});
const model = llm(process.env.LLM_MODEL || "deepseek-chat");

const routeSchema = z.object({
  skill: z.string().describe("要激活的技能名称"),
  reasoning: z.string().describe("选择该技能的原因（中文）"),
});

export interface RouteResult {
  skill: Skill;
  reasoning: string;
}

export async function routeToSkill(
  message: string,
  hasFileAttachment: boolean,
): Promise<RouteResult> {
  // Fast path: file attachment always triggers data-ingest
  if (hasFileAttachment) {
    const skill = loadSkillFull("data-ingest");
    if (skill) return { skill, reasoning: "用户上传了文件" };
  }

  const skillIndex = buildSkillIndexPrompt();

  const result = await generateObject({
    model,
    schema: routeSchema,
    prompt: `用户消息: "${message}"

${skillIndex}

根据用户消息选择最合适的技能。输出技能名称和原因。`,
    maxTokens: 200,
  });

  const chosen = loadSkillFull(result.object.skill);
  if (!chosen) {
    const fallback = loadSkillFull("general-chat")!;
    return { skill: fallback, reasoning: "未匹配到技能，使用通用对话" };
  }

  return { skill: chosen, reasoning: result.object.reasoning };
}
```

- [ ] **Step 2: Commit**

```bash
git add v3/nextjs/src/app/agent/skill-router.ts
git commit -m "feat: add skill-router with LLM-based routing + file fast-path"
```

---

### Task 4: Add 3 new Tools to tool-registry.ts

**Files:**
- Modify: `v3/nextjs/src/app/agent/tool-registry.ts`

- [ ] **Step 1: Add ingest_file, create_ontology, list_my_data tools**

Append after the existing `loadAllTools` function:

```typescript
export function buildIngestTools(): Record<string, Tool> {
  return {
    ingest_file: {
      name: "ingest_file",
      description: "上传并解析用户的数据文件（CSV/Excel），返回列名和类型推断结果",
      execute: async (params: Record<string, any>) => {
        const fd = new FormData();
        fd.append("type", params.file_type || "csv");
        if (params.file_path) fd.append("path", params.file_path);
        return pythonFetch("/ingest", { method: "POST", body: fd });
      },
    },
    create_ontology: {
      name: "create_ontology",
      description: "根据数据 schema 自动生成本体并注册，用户不需要看到 YAML",
      execute: async (params: Record<string, any>) => {
        const columns = params.columns as Array<{ name: string; semantic_type: string }>;
        const tableName = params.table_name || "data";
        const props = columns
          .map((c) => `      - name: ${c.name}\n        source_column: ${c.name}\n        semantic_type: ${c.semantic_type}`)
          .join("\n");
        const yaml = `name: ${tableName}-auto\nslug: ${tableName}-auto\nobjects:\n  - name: ${tableName.charAt(0).toUpperCase() + tableName.slice(1)}\n    slug: ${tableName}\n    table_name: ${tableName}\n    properties:\n${props}`;
        return pythonFetch("/ontology", {
          method: "POST",
          body: JSON.stringify({ yaml_source: yaml }),
        });
      },
    },
    list_my_data: {
      name: "list_my_data",
      description: "列出用户已有的所有数据集和本体，用于判断用户问的数据是否已存在",
      execute: async () => {
        const [ontologies, datasources] = await Promise.all([
          pythonFetch("/ontology").catch(() => []),
          pythonFetch("/datasources").catch(() => []),
        ]);
        return {
          ontologies: ontologies.map((o: any) => ({ id: o.id, name: o.name, slug: o.slug })),
          datasources: datasources.map((d: any) => ({
            id: d.id, name: d.name, type: d.type,
            datasets: d.datasets?.map((ds: any) => ({ table: ds.table_name, rows: ds.rows_count })),
          })),
        };
      },
    },
  };
}
```

- [ ] **Step 2: Add schemaForTool entries in react.ts**

Add to the `schemaForTool` function in `react.ts`:

```typescript
  if (name === "ingest_file") {
    return z.object({
      file_type: z.enum(["csv", "excel"]).describe("文件类型"),
      file_path: z.string().optional().describe("服务端暂存的文件路径"),
    });
  }
  if (name === "create_ontology") {
    return z.object({
      table_name: z.string().describe("数据表名"),
      columns: z.array(z.object({
        name: z.string(),
        semantic_type: z.string(),
      })).describe("列定义"),
    });
  }
  if (name === "list_my_data") {
    return z.object({});
  }
```

- [ ] **Step 3: Commit**

```bash
git add v3/nextjs/src/app/agent/tool-registry.ts v3/nextjs/src/app/agent/react.ts
git commit -m "feat: add ingest_file, create_ontology, list_my_data tools"
```

---

### Task 5: Modify react.ts — accept skill instructions instead of plan

**Files:**
- Modify: `v3/nextjs/src/app/agent/react.ts`

- [ ] **Step 1: Change executeReactStream signature**

Replace the `plan` parameter with `skillInstructions`:

```typescript
export async function executeReactStream(
  question: string,
  skillInstructions: string,
  tools: Record<string, Tool>,
  onToolCall: (call: ToolCallEvent) => void,
  onToken: (token: string) => void,
): Promise<void> {
  const system = `你是中小企业数据分析助手。

${skillInstructions}

用中文清晰回答用户问题。
- 数据用具体数字说话
- 给出业务洞察，不仅是数字`;

  // ... rest of function unchanged (aiTools loop, streamText call)
```

The key change: `system` prompt now uses `skillInstructions` (the SKILL.md body) instead of a generated plan text.

- [ ] **Step 2: Commit**

```bash
git add v3/nextjs/src/app/agent/react.ts
git commit -m "refactor: react.ts accepts skill instructions instead of plan"
```

---

### Task 6: Rewrite send/route.ts — skill-driven flow

**Files:**
- Rewrite: `v3/nextjs/src/app/api/chat/sessions/[id]/send/route.ts`

- [ ] **Step 1: Rewrite with skill router**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { routeToSkill } from "@/app/agent/skill-router";
import { loadAllTools, buildIngestTools } from "@/app/agent/tool-registry";
import { executeReactStream } from "@/app/agent/react";
import { pythonFetch } from "@/services/pythonApi";

export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const formData = await req.formData();
  const message = formData.get("message") as string || "";
  const file = formData.get("file") as File | null;

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      let closed = false;
      const send = (event: string, data: any) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
        } catch {
          closed = true;
        }
      };

      const abort = () => { closed = true; };
      req.signal.addEventListener("abort", abort);

      try {
        // Step 1: Handle file upload if present
        let fileContext = "";
        if (file) {
          send("status", { text: "正在解析文件..." });
          const fd = new FormData();
          fd.append("type", file.name.endsWith(".csv") ? "csv" : "excel");
          fd.append("file", file);
          try {
            const ingestResult = await pythonFetch("/ingest", { method: "POST", body: fd });
            fileContext = `\n\n[文件已上传] 表名: ${ingestResult.table_name}, ${ingestResult.rows_count} 行, 列: ${ingestResult.columns.map((c: any) => `${c.name}(${c.semantic_type})`).join(", ")}, dataset_id: ${ingestResult.dataset_id}`;
          } catch (err: any) {
            send("done", { message: `文件解析失败: ${err.message}` });
            controller.close();
            return;
          }
        }

        if (closed) return;

        // Step 2: Route to skill
        const { skill, reasoning } = await routeToSkill(message + fileContext, !!file);
        send("skill", { name: skill.frontmatter.name, reasoning });

        if (closed) return;

        // Step 3: Load tools
        let tools: Record<string, any> = {};

        // Always include ingest tools (for data-ingest skill)
        Object.assign(tools, buildIngestTools());

        // Load ontology-based tools (for data-query skill)
        try {
          const ontList = await pythonFetch("/ontology");
          if (ontList.length > 0) {
            const schemas = await Promise.all(
              ontList.map((o: any) => pythonFetch(`/ontology/${o.id}/schema`).catch(() => null))
            );
            const { loadAllTools } = await import("@/app/agent/tool-registry");
            Object.assign(tools, await loadAllTools(schemas.filter(Boolean)));
          }
        } catch {}

        if (closed) return;

        // Step 4: Execute with skill instructions
        const fullMessage = message + fileContext;
        const statusMap: Record<string, string> = {
          "data-ingest": "正在解析文件...",
          "data-query": "正在查询数据...",
          "data-explore": "正在查看数据...",
          "general-chat": "思考中...",
        };
        send("status", { text: statusMap[skill.frontmatter.name] || "处理中..." });

        await executeReactStream(
          fullMessage,
          skill.body,
          tools,
          (toolCall) => send("tool", toolCall),
          (token) => send("token", { text: token }),
        );

        send("done", {});
      } catch (err: any) {
        send("error", { message: err.message || "处理请求时出错" });
      } finally {
        req.signal.removeEventListener("abort", abort);
        if (!closed) controller.close();
      }
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
```

- [ ] **Step 2: Delete planner.ts**

```bash
rm v3/nextjs/src/app/agent/planner.ts
```

- [ ] **Step 3: Commit**

```bash
git add v3/nextjs/src/app/api/chat/sessions/[id]/send/route.ts
git rm v3/nextjs/src/app/agent/planner.ts
git commit -m "feat: rewrite send/route.ts with skill-driven flow, delete planner"
```

---

### Task 7: Chat page — file upload + collapsible details

**Files:**
- Modify: `v3/nextjs/src/app/(app)/chat/page.tsx`

- [ ] **Step 1: Add file upload to chat input**

In the input area at the bottom of chat/page.tsx, add a file input before the text input:

```tsx
{/* File upload */}
<label className="cursor-pointer px-3 py-2 border border-gray-200 rounded-lg text-text-secondary hover:bg-data text-sm">
  📎
  <input
    type="file"
    accept=".csv,.xlsx,.xls"
    className="hidden"
    onChange={(e) => {
      const f = e.target.files?.[0];
      if (f) setPendingFile(f);
      e.target.value = "";
    }}
  />
</label>
{pendingFile && (
  <span className="text-xs text-accent truncate max-w-32">
    {pendingFile.name}
  </span>
)}
```

Add state: `const [pendingFile, setPendingFile] = useState<File | null>(null);`

- [ ] **Step 2: Modify handleSend to send FormData with file**

Change the fetch call in handleSend from JSON to FormData:

```typescript
const fd = new FormData();
fd.append("message", text);
if (pendingFile) {
  fd.append("file", pendingFile);
  setPendingFile(null);
}
const res = await fetch(`/api/chat/sessions/${sess.id}/send`, {
  method: "POST",
  body: fd,
  // No Content-Type header — browser sets multipart boundary
});
```

Remove the old `headers: { "Content-Type": "application/json" }` and `JSON.stringify`.

- [ ] **Step 3: Handle new SSE events (skill, status)**

In the SSE parsing loop, add handlers for the new event types:

```typescript
if (event === "skill") {
  // Store for collapsible detail
  last.skill = payload;
} else if (event === "status") {
  last.status = payload.text;
} else if (event === "tool") {
  // existing handler
} else if (event === "token") {
  // existing handler
}
```

- [ ] **Step 4: Add collapsible skill/tool details**

Replace the existing tool call display with a unified collapsible section:

```tsx
{(msg.skill || msg.toolCalls?.length) && (
  <details className="bg-surface border border-gray-200 rounded text-xs mt-1">
    <summary className="cursor-pointer p-2 text-text-secondary">
      技术详情
    </summary>
    <div className="p-2 space-y-1">
      {msg.skill && (
        <div className="text-text-secondary">
          技能: <code className="text-accent">{msg.skill.name}</code>
          <span className="ml-2">{msg.skill.reasoning}</span>
        </div>
      )}
      {msg.toolCalls?.map((tc: any, j: number) => (
        <div key={j}>
          <span className={tc.status === "success" ? "text-cool" : "text-red-500"}>
            {tc.status === "success" ? "✓" : "✗"}
          </span>
          {" "}<code className="text-accent">{tc.toolName}</code>
          {tc.result?.matched && ` → ${tc.result.matched.length} 条`}
        </div>
      ))}
    </div>
  </details>
)}
```

- [ ] **Step 5: Add status indicator during streaming**

Show the lightweight status text while streaming:

```tsx
{streaming && msg.status && (
  <div className="text-xs text-text-secondary italic animate-pulse">
    {msg.status}
  </div>
)}
```

- [ ] **Step 6: Update Message type**

Add `skill` and `status` to the Message type:

```typescript
type Message = {
  role: "user" | "assistant";
  content: string;
  plan?: any;           // keep for backward compat, will be unused
  toolCalls?: ToolCall[];
  skill?: { name: string; reasoning: string };
  status?: string;
};
```

- [ ] **Step 7: Commit**

```bash
git add v3/nextjs/src/app/(app)/chat/page.tsx
git commit -m "feat: chat page with file upload, skill status, collapsible details"
```

---

### Task 8: Build verification + cleanup

- [ ] **Step 1: TypeScript check**

```bash
cd v3/nextjs && npx tsc --noEmit
```

Expected: PASS (0 errors)

- [ ] **Step 2: Next.js build**

```bash
npx next build
```

Expected: ✓ Compiled successfully

- [ ] **Step 3: Remove unused planner import from any file**

```bash
grep -rn "planner" v3/nextjs/src/ --include="*.ts" --include="*.tsx"
```

If any imports remain, remove them.

- [ ] **Step 4: Python tests still pass**

```bash
cd v3/python-api && source .venv/bin/activate && pytest tests/ -q
```

Expected: 30 passed (Python unchanged)

- [ ] **Step 5: Final commit**

```bash
git add -A v3/
git commit -m "chore: build verification, cleanup stale planner references"
```
