# Ontology Map 本体地图 Design Spec

> **For agentic workers:** Use superpowers:executing-plans to implement this plan.

**Goal:** 为 Omaha OntoCenter 项目添加一个全屏本体地图页面，让非技术用户（决策者、业务方）能直观理解项目的业务数据模型，并从图谱直接进入查询。

**Architecture:** 独立全屏页面 `/projects/:id/map`，ECharts 渲染两种视图（ER 图 + 知识图谱），复用已有 semantic API 和 query API，零新依赖。

**Tech Stack:** React 18 + TypeScript + ECharts（已有）+ shadcn/ui + Tailwind CSS（OLED Dark 主题）

---

## 文件结构

```
frontend/src/
├── pages/
│   └── OntologyMap.tsx              # 新建：页面主组件，数据加载，视图切换
├── components/map/
│   ├── ERDiagram.tsx                # 新建：ER 图视图
│   ├── KnowledgeGraph.tsx           # 新建：知识图谱视图
│   └── NodeDetailDrawer.tsx         # 新建：底部详情抽屉
```

修改文件：
- `frontend/src/App.tsx` — 新增路由
- `frontend/src/pages/ProjectDetail.tsx` — Ontology Tab 增加入口按钮
- `frontend/src/pages/ObjectExplorer.tsx` — 支持从 location.state 读取 `preselect` 字段自动选中对象类型

---

## 数据结构

**关系数据来源：** `SemanticObject.relationships: any[]`（每个对象内部各自携带关系数组）。前端在 `OntologyMap.tsx` 中将所有对象的 relationships 扁平化去重，构建全局边列表。

```ts
// 从 parsed.objects 提取关系边
const edges = Object.entries(objects).flatMap(([objName, obj]) =>
  obj.relationships
    .filter(r => r.from_object === objName) // 只取 from 方，避免重复
    .map(r => ({ source: r.from_object, target: r.to_object, label: r.name }))
);
```

**样本数据 API：** 使用已有 `POST /query/:projectId/query`（`queryService.queryObjects`），limit=3，仅查询前 5 个 base_properties 字段（避免字段过多时的性能问题）。

---

## 视图设计

### ER 图（ERDiagram）

- ECharts `graph` 类型，`layout: 'none'`（手动网格定位）
- 节点：圆角矩形（`symbol: 'roundRect'`），显示对象名 + 字段数
- 布局：每行 3 个，间距 280px × 200px，自动计算坐标
- 边：有向箭头 + 关系名标签，`1:N` 关系用实线，引用关系用虚线（通过 `lineStyle.type` 区分）
- 切换到知识图谱时：保存当前选中节点名，切换后高亮同名节点

### 知识图谱（KnowledgeGraph）

- ECharts `graph` 类型，`layout: 'force'`，`draggable: true`
- `symbolSize` = 40 + 字段数 × 2（上限 80）
- 切换到 ER 图前：调用 `chart.dispose()` 停止力导向模拟，避免状态残留
- 支持鼠标拖拽节点重新定位（`draggable: true`）
- 项目 id 变化时（useEffect 依赖 projectId）重新 dispose 并 init，避免内存泄漏

### 节点颜色系统（颜色 + 图标 + 文字三重表达）

`SemanticObject` 类型无 category 字段，通过对象名称关键词匹配推断类型（在 `OntologyMap.tsx` 中实现 `inferNodeType(name: string)` 函数）：

```ts
function inferNodeType(name: string): 'quote' | 'financial' | 'computed' | 'core' {
  const n = name.toLowerCase();
  if (/quote|daily|price|行情/.test(n)) return 'quote';
  if (/financial|indicator|财务|fina/.test(n)) return 'financial';
  if (/technical|computed|技术|calc/.test(n)) return 'computed';
  return 'core';
}
```

| 类型 | 颜色 | 语义 |
|------|------|------|
| `quote` | `#16a34a` 绿 | 时序行情 |
| `financial` | `#d97706` 琥珀 | 财务指标 |
| `computed` | `#7c3aed` 紫 | 计算衍生 |
| `core`（默认） | `#2563EB` 蓝 | 核心实体 |

---

## 布局结构

```
┌──────────────────────────────────────────────────────┐
│ ← 返回项目   [项目名] 本体地图     [ER图] [知识图谱]   │  ← 48px 顶栏
├──────────────────────────────────────────────────────┤
│                                                      │
│              ECharts 图谱（全屏，calc(100vh-48px)）   │
│       节点可点击 · 滚轮缩放 · 拖拽平移                 │
│                                                      │
├──────── 点击节点后底部滑入 280px ────────────────────┤
│  📈 Stock · 7个字段              [→ 前往 Explorer]   │
│  ──────────────────────────────────────────────────  │
│  ts_code    name      industry   area                │
│  000001.SZ  平安银行   银行       深圳                │
│  600036.SH  招商银行   银行       深圳                │
│  000002.SZ  万科A      房地产     深圳                │
└──────────────────────────────────────────────────────┘
```

**抽屉跳转目标：** `navigate(\`/projects/${projectId}/explorer\`)` 并通过 `location.state` 传入 `{ preselect: objectName }`，ObjectExplorer 读取后自动选中该对象类型。

---

## UX 规范（UI/UX Pro Max）

| 规则 | 实现方式 |
|------|---------|
| `touch-target-size ≥ 44px` | ECharts symbolSize 最小 44，点击区域用 `silent: false` |
| `press-feedback 150ms` | 节点 emphasis 高亮，`animationDurationUpdate: 150` |
| `modal-motion 250ms ease-out` | 抽屉 `transition: transform 250ms cubic-bezier(0,0,0.2,1)` |
| `escape-routes` | ESC 关闭抽屉（keydown listener），顶栏返回按钮 |
| `progressive-loading` | 抽屉内样本数据加载时显示 3 行骨架屏 |
| `color-not-only` | 节点颜色 + label 文字 + tooltip 文字三重表达 |
| `continuity` | 切换视图时保持选中节点，切换后重新高亮 |
| `reduced-motion` | `@media (prefers-reduced-motion)` 禁用 ECharts 动画 |
| `keyboard-nav` | 顶栏按钮可 Tab 聚焦，抽屉关闭按钮可 Enter 触发 |
| `cursor-pointer` | ECharts `cursor: 'pointer'` on nodes |

---

## API 接口

| 接口 | 服务 | 用途 |
|------|------|------|
| `GET /api/v1/projects/:id/semantic` | `semanticApi.get(projectId)` | 获取本体结构 |
| `POST /query/:id/query` | `queryService.queryObjects(id, type, cols, [], [], 3)` | 获取样本数据 |

---

## 路由接入

**App.tsx 新增：**
```tsx
<Route path="projects/:id/map" element={<OntologyMap />} />
```

**ProjectDetail.tsx Ontology Tab 新增按钮：**
```tsx
<Button onClick={() => navigate(`/projects/${projectId}/map`)}>
  查看本体地图
</Button>
```

---

## 不在范围内

- 图谱上直接编辑本体（编辑仍在 SemanticEditor）
- 公开无需登录的演示链接
- 移动端适配（桌面优先）
- 搜索/过滤节点（对象数量少时不需要，可后续迭代）
