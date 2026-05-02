# 补齐 Chat 全操作覆盖 — 实施计划

> **目标**：让 boss 通过对话能完成 v3 平台内的所有常用操作，并且不能完成的操作要明确拒绝+引导，不再出现"假装做"的情况。

## 背景：真实测试发现的 4 个 gap

| 场景 | 当前行为 | 问题 |
|---|---|---|
| "删掉我刚才上传的数据" | data-ingest + create_ontology 被调用 | **高危幻觉**：不但没删，反创建重复本体 |
| "把订单编号改名成单号" | data-query 查数据"看看" | **假装做**：agent 不能改但也没说不能 |
| "我想连 MySQL" | data-explore 回复查询建议 | **文不对题**：agent 不具备能力 |
| "给我 API key" | general-chat → "思考中..." | **无能但未引导**：应该告诉用户去哪里做 |

## 关键洞察

**后端几乎都已就绪**：
- ✅ `DELETE /ontology/{id}`, `DELETE /datasources/{id}` — 删除能力
- ✅ `PUT /ontology/{id}` — 本体整体重建（含改列名/类型）
- ✅ `POST /ingest` with `type=mysql/postgres/sqlite` — 接外部 DB
- ✅ `POST /api/keys` (Next.js) — 创建 API key
- ✅ Next.js `/settings/api-keys`, `/datasources/connect`, `/ontology/{id}` UI 已有

**缺口全在 agent 层**：tool 没暴露 + skill 没覆盖 + LLM 误判 + 边界不清晰。

---

## 方案：双管齐下

### 方案 A：补齐能力（chat 里真能做）
给 agent 增加删除类工具 + 管理类技能，让 chat 能完成更多操作。

### 方案 B：明亮边界（chat 不能做的明确引导）
改 general-chat skill + 新增 out-of-scope fallback，遇到不支持的意图时**明确告诉用户去哪个菜单做**。

**双管齐下**：A 做高频高价值操作（删除、改列名），B 兜底不支持的（连 DB、管 key）。

---

## Task Breakdown

### Task 1: 补后端小缺口 — 重命名本体/数据集

**Files:**
- Modify: `v3/python-api/app/api/ontology.py` — add `PATCH /ontology/{id}/rename` that only changes name/description (vs PUT which rebuilds everything)
- Modify: `v3/python-api/app/api/datasources.py` — add `PATCH /datasources/{id}/rename`

**Why:** 用 PUT 整体重建 YAML 来改名太重（会重 drop & recreate 所有 DuckDB 视图）。PATCH 只改 name 字段，O(1)。

- [ ] **Step 1.1: ontology rename**
```python
@router.patch("/{ontology_id}/rename")
async def rename_ontology(
    ontology_id: str, tenant_id: TenantId,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    ont = await _require_ontology(db, ontology_id, tenant_id)
    new_name = (body.get("name") or "").strip()
    if not new_name:
        raise HTTPException(400, "name required")
    ont.name = new_name[:128]
    if "description" in body:
        ont.description = str(body["description"] or "")[:500]
    await db.commit()
    return {"id": ont.id, "name": ont.name}
```

- [ ] **Step 1.2: datasource rename**

Same pattern, on `DataSource.name`.

- [ ] **Step 1.3: Tests + commit**

Add 2 tests to `test_ontology_listing.py` / `test_e2e.py`. Commit.

---

### Task 2: 新增 data-manage skill + 3 个管理工具

**Files:**
- Create: `v3/nextjs/src/skills/data-manage/SKILL.md`
- Modify: `v3/nextjs/src/app/agent/skills.ts` — add `DATA_MANAGE` constant
- Modify: `v3/nextjs/src/app/agent/tool-registry.ts` — add `buildManageTools(tenantId)`
- Modify: `v3/nextjs/src/app/agent/react.ts` — add schemas for new tools
- Modify: `v3/nextjs/src/app/agent/skill-router.ts` — add MANAGE heuristic keywords
- Modify: `v3/nextjs/src/app/api/chat/sessions/[id]/send/route.ts` — load manage tools when skill is data-manage

- [ ] **Step 2.1: SKILL.md**

```markdown
---
name: data-manage
description: 用户要对已有数据集进行管理操作时触发：删除、重命名、修改列
triggers:
  - "删除"、"删掉"、"删了"
  - "改名"、"重命名"、"叫作"
  - "改列"、"改字段"、"改成"
  - "修改数据"
---

# 数据管理助手

用户要对已有的数据集（本体）做修改或删除。

## 步骤

1. 调用 `list_my_data` 确认用户指的是哪个数据集（如果模糊）
2. **执行破坏性操作前必须先确认** — 不要直接调用删除工具
   - 对用户说："确认要删除 '订单' 数据集吗？这个操作不可撤销。"
   - 等用户明确说"确认"、"是的"、"可以"才执行
3. 调用相应工具：
   - 删除整个数据集 → `delete_ontology`
   - 重命名数据集 → `rename_ontology`  
   - 修改列（改名/改类型） → `recreate_ontology_with_schema`（会重建本体但数据保留）
4. 操作完成后告诉用户结果

## 规则

- 破坏性操作（删除）必须二次确认
- 不支持的操作（如：只改一列不重建）告诉用户："目前没法只改一列，需要我帮你重建整个本体吗？这样数据保留但列定义会刷新。"
- 绝不展示 YAML/ID/技术细节
```

- [ ] **Step 2.2: Register SKILL constant**

`skills.ts`:
```typescript
export const SKILLS = {
  DATA_INGEST: "data-ingest",
  DATA_QUERY: "data-query",
  DATA_EXPLORE: "data-explore",
  DATA_MANAGE: "data-manage",      // new
  GENERAL_CHAT: "general-chat",
} as const;

export const DATA_SKILLS: ReadonlySet<string> = new Set([
  SKILLS.DATA_QUERY, SKILLS.DATA_EXPLORE, SKILLS.DATA_MANAGE,  // add manage
]);

export const SKILL_STATUS: Record<string, string> = {
  ...,
  [SKILLS.DATA_MANAGE]: "正在处理...",
};
```

- [ ] **Step 2.3: buildManageTools**

`tool-registry.ts`:
```typescript
export function buildManageTools(tenantId: string): Record<string, Tool> {
  return {
    delete_ontology: {
      name: "delete_ontology",
      description: "删除指定的数据集/本体（不可撤销）。必须先获得用户明确确认",
      execute: async (params) => {
        const id = String(params.ontology_id);
        // pythonApi.ts already has delete — add wrapper if not:
        return ontologyApi.delete(id, tenantId);
      },
    },
    rename_ontology: {
      name: "rename_ontology",
      description: "重命名数据集。参数：ontology_id, new_name",
      execute: async (params) =>
        pythonFetch(`/ontology/${params.ontology_id}/rename?tenant_id=${tenantId}`, {
          method: "PATCH",
          body: JSON.stringify({ name: params.new_name }),
        }),
    },
    recreate_ontology_with_schema: {
      name: "recreate_ontology_with_schema",
      description: "重建本体（修改列定义）。数据保留，仅本体定义更新。参数：ontology_id, columns[{name, semantic_type}]",
      execute: async (params) => {
        // TODO: reuse buildOntologyYaml, call PUT /ontology/{id}
      },
    },
  };
}
```

- [ ] **Step 2.4: Add schemas in react.ts schemaForTool**

```typescript
if (name === "delete_ontology") return z.object({ ontology_id: z.string() });
if (name === "rename_ontology") return z.object({ ontology_id: z.string(), new_name: z.string() });
if (name === "recreate_ontology_with_schema") return z.object({
  ontology_id: z.string(),
  columns: z.array(z.object({ name: z.string(), semantic_type: z.string() })),
});
```

- [ ] **Step 2.5: Heuristic keywords**

`skill-router.ts`:
```typescript
const MANAGE_KEYWORDS = ["删除", "删掉", "删了", "重命名", "改名", "叫作", "改列", "改字段", "修改数据"];
// ... in heuristicRoute:
if (MANAGE_KEYWORDS.some(k => raw.includes(k))) {
  return SKILLS.DATA_MANAGE;
}
```
顺序：放在 INGEST 之后、QUERY 之前。避免 `"删了重新上传"` 这种误配 ingest。

- [ ] **Step 2.6: Wire in send/route.ts**

```typescript
if (skill.frontmatter.name === SKILLS.DATA_MANAGE) {
  Object.assign(tools, buildManageTools(tenantId));
  // Still load query tools too — user might reference data in the same turn
  Object.assign(tools, loadAllTools(schemas, tenantId));
}
```

---

### Task 3: general-chat 升级为 "out-of-scope fallback"

**Files:**
- Modify: `v3/nextjs/src/skills/general-chat/SKILL.md`

**Why:** 现在 general-chat 只说"友好回应"。需要识别"不支持的操作"并给出具体引导。

- [ ] **Step 3.1: 改写 SKILL.md body**

```markdown
---
name: general-chat
description: 闲聊、问候，或者用户意图我不支持时的兜底。明确告诉用户能做什么、去哪里做
triggers:
  - 问候
  - 用户要求的操作 agent 做不了
---

# 通用对话 + 不支持操作的引导

## 规则

1. 普通问候（"你好"、"谢谢"）→ 友好简短回应，引导"有什么数据想分析吗？"

2. 用户要求以下操作但 agent 无法完成 → **明确告诉去哪里做**：

   | 用户说 | 回复模板 |
   |---|---|
   | 要连 MySQL/Postgres/外部数据库 | "连接外部数据库需要填主机、账号等信息，请到左侧菜单【数据源 → 连接数据源】页面填写。" |
   | 要 API key / 想在 Cursor/the assistant Desktop 里用 | "生成 API key 请到【设置 → API Keys】，点'生成新密钥'按钮即可。" |
   | 要注册新用户 / 邀请团队成员 | "这个功能还在开发中，目前使用 demo 账号。" |
   | 其他明显与数据分析无关的问题（天气、写代码等） | 礼貌说"我专注于帮你分析业务数据，这个问题帮不上忙" |

3. **绝不伪装做事**：如果不确定能不能做，说"这个我可能做不了，你可以..."，不要调用工具假装尝试。

4. 不要调用任何工具 —— 这个技能纯对话。
```

---

### Task 4: 加一个"confirmation sticky"防删除误操作

**Files:**
- Modify: `v3/nextjs/src/app/api/chat/sessions/[id]/send/route.ts`

**Why:** data-manage 删除必须二次确认。如果上一轮 assistant 问"确认删除吗？"，这一轮必须粘到 data-manage（防止 heuristic 把 "确认"/"是的" 路由到其他 skill）。

- [ ] **Step 4.1: 识别"pending confirmation"**

扩展现有 `isPostUploadTurn` 的思路：

```typescript
const lastAssistantMessage = historyRows.find((m) => m.role === "assistant");
const CONFIRM_PHRASES = ["确认要删除", "这个操作不可撤销", "确认要重命名"];
const isPendingManageConfirmation = 
  !file &&
  lastAssistantMessage?.content &&
  CONFIRM_PHRASES.some(p => lastAssistantMessage.content.includes(p));

// after routing:
if (isPendingManageConfirmation && skill.frontmatter.name !== SKILLS.DATA_MANAGE) {
  skill = mustLoadSkill(SKILLS.DATA_MANAGE);
  reasoning = "上一轮询问删除确认，本轮继续管理流程";
}
```

---

### Task 5: 端到端 smoke

重新跑 T1-T4 验证：

| 测试 | 预期 |
|---|---|
| T1 "删掉我刚才上传的数据" | skill=data-manage, LLM 先问确认，不立即调用 delete |
| T1b "确认" | sticky manage, 调用 delete_ontology, 成功回复 |
| T2 "把'客户'列改名成'用户名'" | skill=data-manage, 调用 recreate_ontology_with_schema |
| T3 "我想连 MySQL" | skill=general-chat, 回复"请到【数据源 → 连接数据源】" |
| T4 "给我 API key" | skill=general-chat, 回复"请到【设置 → API Keys】" |

---

## 显式不做（punt）

- **连接 MySQL 通过 chat** — 太多参数（host/port/user/pass/db），chat 不是合适媒介，UI 已经有。
- **API key 通过 chat 创建** — 一次性展示 plaintext 只适合 UI，chat 里无法安全处理。
- **注册新用户** — 这是整体 auth 重做的事（P6 级别）。
- **撤销操作（undo）** — 本 v3 没有事件溯源，做不了真 undo。"二次确认"就是唯一保障。
- **批量删除** — 单次只删一个数据集，批量风险太高。

## 工作量估计

| Task | 文件数 | 估时 |
|---|---|---|
| 1 (backend rename) | 2 Py + 1 test | 1h |
| 2 (data-manage skill + tools) | 6 TS + 1 SKILL.md | 3h |
| 3 (general-chat rewrite) | 1 SKILL.md | 30m |
| 4 (confirmation sticky) | 1 TS | 30m |
| 5 (E2E smoke) | 重跑现有脚本 | 30m |
| **总计** | | **~5.5h** |

## 风险

- **R1: Heuristic 误路由**。`"删除"` 出现在很多非管理场景（"删除这条过滤"）。Mitigation: MANAGE_KEYWORDS 测试集覆盖。
- **R2: LLM 不听话**。SKILL.md 让 LLM "先确认"，但温度高时可能直接删。Mitigation: `delete_ontology` 工具本身额外要求 `confirmed: true` 参数，由 LLM 显式传。
- **R3: Out-of-scope fallback 误拒绝真诉求**。用户说"能不能改下列名"其实是真需求，但 general-chat 把它当 out-of-scope。Mitigation: 这个要归到 data-manage skill，通过 MANAGE_KEYWORDS 的"改列"/"改字段"正确路由。
