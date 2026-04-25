# Phase 3b：对话式建模增强 — Agent 集成 + 行业模板 + 编辑能力

## 1. 目标

让用户在对话里完成完整的"接入 → 清洗 → 建模 → 查询"主线，无需跳到独立 REST API。Agent 主动推进建模，结合行业模板提升推断准确率，确认后允许通过对话修改本体。

这是 Phase 3a "对话式数据接入" 的直接延续。

## 2. 范围

**包含：**
- 5 个新 Agent 工具：`load_template`、`scan_tables`、`infer_ontology`、`confirm_ontology`、`edit_ontology`
- 草稿存储：`OntologyDraftStore`（pickle，按 project+session 隔离）
- 行业模板系统：`TemplateLoader` + `configs/templates/retail.yaml`
- 模板 + 推断混合策略：模板提示 LLM 映射 + 代码层硬补语义类型
- 前端 `OntologyConfirmPanel` 富组件（panel_type: ontology_preview）
- Agent 主动推进：清洗完成后 → 主动建议建模

**不包含（推迟到后续）：**
- 草稿期字段级编辑（必须 confirm 之后才能用 edit_ontology）
- 制造/贸易/服务模板（先做零售，其他按需）
- 模板编辑 UI（用户只能选用，不能创建模板）
- 跳过建模的旁路（建模是必经环节）

## 3. 数据流

```
用户上传文件
    ↓
[Phase 3a] assess_quality → 用户确认清洗 → clean_data
    ↓
Agent 主动："要不要把数据整理成业务对象？"
    ↓
load_template (用户选行业 / 从 setup metadata 读)
    ↓
scan_tables (UploadedTableStore → TableSummary[])
    ↓
infer_ontology (LLM + template_hint → 草稿 pickle)
    ↓
返回 panel_type: ontology_preview 卡片
    ↓
用户点 "确认" → confirm_ontology → setup_stage = ready
用户点 "重新分析" → 重跑 infer_ontology（覆盖草稿）
    ↓
[setup_stage = ready 后]
用户："把订单的金额字段改成货币类型" → edit_ontology
```

## 4. 后端服务

### 4.1 OntologyDraftStore

按 `(project_id, session_id)` 隔离的 pickle 草稿存储。

```python
class OntologyDraftStore:
    @staticmethod
    def save(project_id, session_id, objects, relationships, warnings) -> None:
        """覆盖写入。新草稿替代旧草稿。"""

    @staticmethod
    def load(project_id, session_id) -> dict | None:
        """返回 {objects, relationships, warnings} 或 None。"""

    @staticmethod
    def clear(project_id, session_id) -> None:
        """删除草稿文件。confirm 成功后调用。"""
```

存储路径：`data/uploads/{project_id}/{session_id}/_drafts/draft.pkl`

### 4.2 TemplateLoader

```python
class TemplateLoader:
    @staticmethod
    def list_industries() -> list[dict]:
        """返回 [{value: 'retail', display_name: '零售/电商', domain: 'retail'}]"""

    @staticmethod
    def load(industry: str) -> dict | None:
        """加载 configs/templates/{industry}.yaml，返回 {objects, relationships}。"""
```

模板 YAML 格式：

```yaml
industry: retail
display_name: 零售/电商
domain: retail
objects:
  - name: 订单
    description: 客户的采购订单
    business_context: 从下单到签收的全生命周期
    properties:
      - name: 订单号
        data_type: string
        semantic_type: order_id
      - name: 金额
        data_type: number
        semantic_type: currency_cny
      - name: 状态
        data_type: string
        semantic_type: order_status
      - name: 下单时间
        data_type: datetime
        semantic_type: datetime
  - name: 客户
    description: 客户档案
    properties:
      - name: 客户名
        data_type: string
        semantic_type: person_name
      - name: 电话
        data_type: string
        semantic_type: phone
  - name: 库存
    description: 商品库存
    properties:
      - name: 商品名
        data_type: string
        semantic_type: product_name
      - name: 数量
        data_type: number
        semantic_type: quantity
relationships:
  - from: 订单
    to: 客户
    type: belongs_to
    from_field: 客户ID
    to_field: ID
```

### 4.3 OntologyInferrer 增强

在现有 `infer_objects()` 加 `template_hint` 参数：

```python
def infer_objects(
    self,
    tables: list[TableSummary],
    template_hint: dict | None = None,  # 模板的简化版（仅对象名+描述+字段名列表）
) -> list[InferredObject]:
    ...

def merge_template_semantic_types(
    inferred: list[InferredObject],
    template: dict,
) -> list[InferredObject]:
    """
    代码层硬补：如果 LLM 把表映射到模板对象名，
    复用模板的字段语义类型（按字段名匹配）。
    """
```

简化模板（给 LLM 看）：

```python
def compact_template(template: dict) -> dict:
    return {
        "objects": [
            {
                "name": obj["name"],
                "description": obj.get("description", ""),
                "field_names": [p["name"] for p in obj.get("properties", [])],
            }
            for obj in template["objects"]
        ],
        "relationships": template.get("relationships", []),
    }
```

LLM Prompt 增量（在 `INFER_PROMPT` 末尾追加）：

```
参考的行业模板（如适用）：
{template_objects_json}

如果某张表的字段和模板中的某个对象高度相似（字段名重叠 50% 以上），
请在输出的 InferredObject.name 字段使用模板中的对象名，
帮助代码层后续复用模板的语义类型定义。
如果不匹配，按你的最佳判断推断。
```

### 4.4 AgentToolkit 5 个新工具

**`load_template`**

```python
{
    "name": "load_template",
    "description": "加载行业模板，返回该行业典型的业务对象定义。在用户告知行业后调用。",
    "parameters": {
        "industry": {"type": "string", "description": "行业代码：retail / manufacturing / trade / service", "required": True}
    }
}
# 返回：{"success": true, "data": {"display_name": "零售/电商", "objects": [...], "relationships": [...]}}
```

**`scan_tables`**

```python
{
    "name": "scan_tables",
    "description": "扫描已上传的数据表，返回每张表的列、行数和样本值。在准备建模前调用。",
    "parameters": {}
}
# 返回：{"success": true, "data": {"tables": [{"name", "row_count", "columns": [{"name", "type"}], "sample_values": {...}}]}}
```

**`infer_ontology`**

```python
{
    "name": "infer_ontology",
    "description": "基于已上传数据 + 可选行业模板推断本体（业务对象、字段语义、关系）。结果存为草稿，用户确认后才生效。",
    "parameters": {
        "industry": {"type": "string", "description": "行业代码（可选）。如有值，会先调 load_template 注入提示", "required": False}
    }
}
# 返回：{"success": true, "data": {"objects_count": 3, "relationships_count": 2}}
# 副作用：写草稿，并通过 structured panel ontology_preview 展示
```

**`confirm_ontology`**

```python
{
    "name": "confirm_ontology",
    "description": "用户确认建模草稿后调用。把草稿持久化到本体库，setup_stage 推到 ready。",
    "parameters": {}
}
# 返回：{"success": true, "data": {"objects_created": 3, "relationships_created": 2}}
```

**`edit_ontology`**（仅修改已确认本体）

```python
{
    "name": "edit_ontology",
    "description": "修改已确认的本体（重命名、改语义类型、增删字段或关系）。setup_stage 必须为 ready 才能调用。",
    "parameters": {
        "action": {
            "type": "string",
            "description": "操作类型：rename_object | rename_property | change_semantic_type | update_description | add_property | remove_property | add_relationship | remove_relationship",
            "required": True
        },
        "object_name": {"type": "string", "required": True},
        "property_name": {"type": "string", "required": False},
        "new_value": {"type": "string", "required": False},
        # add_property 额外参数
        "data_type": {"type": "string", "required": False},
        "semantic_type": {"type": "string", "required": False},
        # add_relationship 额外参数
        "to_object": {"type": "string", "required": False},
        "from_field": {"type": "string", "required": False},
        "to_field": {"type": "string", "required": False},
    }
}
```

### 4.5 setup_stage 状态推进

| 触发 | 旧状态 | 新状态 |
|------|-------|--------|
| `clean_data` 工具成功 | cleaning | modeling |
| `confirm_ontology` 工具成功 | modeling | ready |

注：`infer_ontology` 不改 setup_stage（草稿期还在 modeling 阶段）。

## 5. 前端

### 5.1 OntologyConfirmPanel 组件

```tsx
interface OntologyPreviewData {
  template_name?: string;
  objects: Array<{
    name: string;
    row_count?: number;
    description?: string;
    properties: Array<{
      name: string;
      data_type: string;
      semantic_type?: string;
    }>;
  }>;
  relationships: Array<{
    from: string;
    to: string;
    from_field: string;
    to_field: string;
  }>;
  warnings: string[];
}

export function OntologyConfirmPanel({ data, onConfirm, onRetry }: Props)
```

UI 行为：
- 默认每个对象折叠状态，点击展开看字段详情
- 顶部显示模板名（如有）
- 底部两个按钮：`✓ 确认建模` / `↻ 重新分析`
- 确认 → 触发 `handleSend("确认建模")` → Agent 调 confirm_ontology
- 重新分析 → 触发 `handleSend("重新分析建模")` → Agent 重跑 infer_ontology

### 5.2 StructuredMessage 扩展

```tsx
case 'panel':
  if (item.panel_type === 'quality_report') {
    return <QualityPanel ... />;
  }
  if (item.panel_type === 'ontology_preview') {
    return <OntologyConfirmPanel
      data={item.data}
      onConfirm={() => onOptionSelect?.("确认建模")}
      onRetry={() => onOptionSelect?.("重新分析建模")}
    />;
  }
  return <p ...>{item.content}</p>;
```

### 5.3 Pydantic 扩展

```python
class PanelResponse(BaseModel):
    type: Literal["panel"] = "panel"
    content: str
    panel_type: Literal["quality_report", "ontology_preview"]
    data: dict[str, Any]
```

## 6. SYSTEM_TEMPLATE 增量

在现有结构化富组件章节增加示例：

````
**展示建模草稿（infer_ontology 工具返回后）：**
```structured
{"type": "panel", "panel_type": "ontology_preview", "content": "我识别出这些业务对象，请确认", "data": {...}}
```
````

工作流工具列表新增 "建模阶段"：

```
**建模阶段**
- load_template: 加载行业模板
- scan_tables: 扫描已上传的数据
- infer_ontology: LLM 推断业务对象 + 字段语义 + 关系（结果写草稿）
- confirm_ontology: 持久化草稿到本体库
- edit_ontology: 修改已确认的本体（仅 setup_stage=ready 时可用）
```

## 7. 测试策略

### 7.1 单元测试

- `test_ontology_draft_store.py`：save/load/clear、覆盖写入、不存在时 load 返回 None
- `test_template_loader.py`：list_industries、load 已知模板、load 未知模板返回 None
- `test_ontology_inferrer.py`（增强）：template_hint 参数、merge_template_semantic_types 字段名匹配
- `test_phase3b_tools.py`：5 个工具的单测（mock LLM、mock UploadedTableStore）

### 7.2 集成测试

- `test_modeling_flow.py`：完整旅程
  1. 上传 CSV
  2. 调用 load_template("retail")
  3. 调用 scan_tables
  4. 调用 infer_ontology(industry="retail")
  5. 验证草稿存在
  6. 调用 confirm_ontology
  7. 验证本体进 DB、setup_stage=ready
  8. 调用 edit_ontology(action="change_semantic_type", ...)
  9. 验证本体更新

### 7.3 前端测试

- OntologyConfirmPanel 组件渲染（mock data）
- 点击 "确认 / 重新分析" 触发对应回调

## 8. 实施分阶段路径（12 个 task）

1. OntologyDraftStore + 测试
2. TemplateLoader + 测试
3. retail.yaml 模板（订单/客户/库存/商品）
4. OntologyInferrer 加 template_hint + compact_template + merge 逻辑
5. AgentToolkit 加 `load_template` + `scan_tables`
6. AgentToolkit 加 `infer_ontology`（含草稿写入 + 结构化 panel 输出）
7. AgentToolkit 加 `confirm_ontology`（含 setup_stage 推进）
8. AgentToolkit 加 `edit_ontology`（8 种 action）
9. ChatService 注册 5 个新 tool schema + dispatch + setup_stage 推进逻辑
10. SYSTEM_TEMPLATE 增加建模工作流文案 + ontology_preview 示例
11. 前端 OntologyConfirmPanel + StructuredMessage 扩展
12. 端到端集成测试

## 9. 复用 Phase 3a 成果

| Phase 3a 资产 | Phase 3b 复用方式 |
|--------------|-------------------|
| UploadedTableStore | scan_tables 直接读取 DataFrame |
| AgentToolkit (project_id, session_id) 构造器 | 5 个新工具同样依赖此上下文 |
| 结构化 `\`\`\`structured\`\`\`` JSON 块 | ontology_preview 走同样路径 |
| ChatService `_extract_structured` | 不需修改，自动处理新 panel_type |
| setup_stage 字段 | 由 clean_data / confirm_ontology 推进 |
| QualityPanel 模式 | OntologyConfirmPanel 仿其结构 |

## 10. 风险与缓解

- **LLM 推断不稳定**：用 temperature=0.1 + 模板硬约束语义类型。"重新分析"按钮兜底。
- **草稿体积过大**：pickle 文件如果对象多可能上 MB。MVP 不限制，监控；后续可改 JSON。
- **edit_ontology action 多**：8 种 action 一个工具承载，参数复杂。LLM 出错时报清晰错误，让用户重新表述。
- **模板覆盖率有限**：MVP 只有 retail。其他行业 fallback 到无模板推断（已支持）。
