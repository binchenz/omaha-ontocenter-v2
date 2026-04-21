# Phase 2a: 本体建模 UI 设计

## 背景

Phase 1 完成了 Connector 框架，支持 SQL/Tushare/CSV/REST 数据源接入。当前用户配置本体的唯一方式是在 Settings → 配置编辑 Tab 手写 YAML。这对非技术用户门槛过高，也容易出错。

Phase 2a 目标：在 Settings 新增「本体建模」Tab，提供可视化表单编辑器，与 YAML 手动双向同步。

## 产品定位

- 目标用户：技术人员（配置本体），业务人员继续用 Explorer/Chat
- 同步方式：手动触发（「生成 YAML」和「从 YAML 导入」按钮），不做实时双向同步
- 不替换 YAML 编辑器，两者并存

## 页面布局

Settings 新增「本体建模」Tab，左右分栏：

```
┌─────────────────────────────────────────────────────────┐
│ Settings: [项目管理] [数据源] [本体建模] [配置编辑] [API Keys] │
├──────────────────────┬──────────────────────────────────┤
│  左侧：结构树 + 表单  │  右侧：YAML 预览                  │
│                      │                                  │
│  📂 数据源            │  datasources:                    │
│  ├ tushare_pro       │    - id: tushare_pro             │
│  └ [+ 添加数据源]     │      type: tushare               │
│                      │      ...                         │
│  📦 对象类型          │  ontology:                       │
│  ├ Stock ▸           │    objects:                      │
│  ├ DailyQuote ▸      │      - name: Stock               │
│  └ [+ 添加对象]       │        ...                       │
│                      │                                  │
│  [从 YAML 导入]      │  [生成 YAML]  [保存到项目]         │
└──────────────────────┴──────────────────────────────────┘
```

点击左侧数据源/对象 → 展开内联编辑表单（在左侧面板内）。

## 数据模型（前端 TypeScript）

```typescript
interface OntologyModel {
  datasources: DatasourceConfig[];
  objects: ObjectConfig[];
}

interface DatasourceConfig {
  id: string;
  name: string;
  type: string; // tushare | sqlite | mysql | postgresql | csv | excel | rest_api
  connection: Record<string, string>;
}

interface ObjectConfig {
  name: string;
  datasource: string;
  table?: string;
  api_name?: string;
  primary_key?: string;
  description?: string;
  properties: PropertyConfig[];
  relationships: RelationshipConfig[];
}

interface PropertyConfig {
  name: string;
  column?: string;
  type: string; // string | integer | decimal | date | datetime | boolean
  semantic_type?: string; // percentage | currency_cny | date | stock_code | text | number
  description?: string;
}

interface RelationshipConfig {
  name: string;
  to_object: string;
  type: string; // one_to_many | many_to_one
  join_condition: { from_field: string; to_field: string };
}
```

## 后端变化

### 新增端点

```
POST /api/v1/ontology/generate
Body: { model: OntologyModel }
Response: { yaml: string, valid: boolean }
```

将 JSON 对象模型序列化为格式化 YAML 字符串。YAML 生成在后端，前端不引入 yaml 库。

### 复用现有端点

- `POST /api/v1/ontology/validate` — 验证生成的 YAML
- `POST /api/v1/ontology/build` — 解析 YAML 为结构化对象（用于「从 YAML 导入」）
- `PUT /api/v1/projects/{id}` — 保存 YAML 到项目

### 后端实现

在 `backend/app/api/ontology.py` 新增 `/generate` 端点，实现 `OntologyModel → YAML` 序列化：

```python
@router.post("/generate")
def generate_yaml(model: OntologyModelRequest, user = Depends(get_current_user)):
    yaml_str = _model_to_yaml(model)
    return {"yaml": yaml_str, "valid": True}
```

`_model_to_yaml` 使用 `yaml.dump()` 将 Pydantic 模型序列化，保持字段顺序和缩进风格与现有 YAML 一致。

## 前端文件结构

```
frontend/src/pages/
├── OntologyEditor.tsx              # 主页面（左右分栏容器）

frontend/src/components/ontology/
├── DatasourceList.tsx              # 数据源列表 + 编辑表单
├── ObjectList.tsx                  # 对象类型列表
├── ObjectForm.tsx                  # 对象编辑表单（名称、数据源、表名等）
├── PropertyTable.tsx               # 字段属性表格（增删改）
├── RelationshipList.tsx            # 关系列表（增删改）
└── YamlPreview.tsx                 # YAML 只读预览 + 操作按钮
```

Settings.tsx 新增 Tab 引用 `OntologyEditor`。

## 交互流程

### UI → YAML（生成）
1. 用户在左侧表单编辑数据源/对象/字段
2. 点击「生成 YAML」→ 调用 `POST /api/v1/ontology/generate`
3. 右侧 YAML 预览更新
4. 点击「保存到项目」→ 调用 `PUT /api/v1/projects/{id}`

### YAML → UI（导入）
1. 用户点击「从 YAML 导入」
2. 读取当前项目的 `omaha_config`
3. 调用 `POST /api/v1/ontology/build` 解析 YAML
4. 将解析结果填充到左侧表单状态

## 测试策略

- 后端：`test_api_ontology.py` 新增 `/generate` 端点测试，覆盖各种对象类型和字段组合
- 前端：TypeScript 零错误 + Vite 构建通过
- 集成：生成 YAML → validate → 保存 → 重新导入，验证往返一致性

## 不在范围内

- 实时双向同步（手动触发已足够）
- 拖拽排序字段（可后续迭代）
- 计算属性（computed property）的可视化编辑（YAML 编辑器处理）
- MongoDB Connector（Phase 2b 单独处理）
