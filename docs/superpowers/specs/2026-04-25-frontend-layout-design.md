# 前端布局重构 — 设计文档

## 1. 目标

将前端从"开发者工具"布局（固定侧边栏）改为"AI原生产品"布局（顶部模块导航 + 左侧子导航），对标Palantir/飞书风格。新旧布局并存，不改动现有代码。

**范围：** 布局骨架 + 路由重构 + v2页面wrapper。不改现有组件逻辑。

## 2. 布局结构

```
┌─────────────────────────────────────────────────────────┐
│  TopNav (48px)                                           │
│  Logo | AI助手  本体  看板  应用  |  ProjectSwitcher  用户  │
├──────────┬──────────────────────────────────────────────┤
│ Module   │  主内容区 (Outlet)                             │
│ Sidebar  │                                              │
│ (200px)  │  当前页面组件                                  │
│          │                                              │
│ 子页面   │                                              │
│ 列表     │                                              │
├──────────┴──────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────┘
```

## 3. 导航模块

| 模块 | 路由前缀 | 子页面 |
|------|---------|--------|
| AI助手 | /app/assistant | 对话, 历史 |
| 本体 | /app/ontology | 对象浏览, 关系图谱, 数据源, 导入/建模 |
| 看板 | /app/dashboard | 我的看板, 模板看板 |
| 应用 | /app/apps | (占位：即将推出) |
| 设置 | /app/settings | 成员, Pipeline, API密钥, 审计日志 |

默认landing page: `/app/assistant`

## 4. 路由配置

```
/app/assistant              → AssistantPage (包装ChatAgent)
/app/assistant/history      → AssistantHistory (包装ChatWithSessions)
/app/ontology               → OntologyBrowser (包装ObjectExplorer)
/app/ontology/graph         → OntologyGraph (包装OntologyMap)
/app/ontology/datasources   → DatasourcePage (包装DatasourceManager)
/app/ontology/modeling      → ModelingPage (新页面，调scan/infer/confirm)
/app/dashboard              → DashboardPage (占位)
/app/dashboard/templates    → DashboardTemplates (占位)
/app/apps                   → AppsPage (占位)
/app/settings               → SettingsPage (包装MembersManager)
/app/settings/pipelines     → PipelinesPage (包装PipelineManager)
/app/settings/api-keys      → ApiKeysPage (包装ApiKeyManager)
/app/settings/audit         → AuditPage (包装AuditLogViewer)
```

旧路由 (`/explorer`, `/chat`, `/settings` 等) 保持不动，走旧MainLayout。

## 5. 新旧并存策略

```tsx
// App.tsx
<Routes>
  {/* 新布局 */}
  <Route path="/app" element={<AppLayout />}>
    <Route path="assistant" element={<AssistantPage />} />
    <Route path="assistant/history" element={<AssistantHistory />} />
    <Route path="ontology" element={<OntologyBrowser />} />
    ...
  </Route>

  {/* 旧布局 — 完全不动 */}
  <Route element={<MainLayout />}>
    <Route path="/explorer" element={<Explorer />} />
    <Route path="/chat" element={<ChatPage />} />
    ...
  </Route>
</Routes>
```

## 6. 文件结构

### 新建

```
frontend/src/layouts/
  AppLayout.tsx         — 新布局壳 (TopNav + ModuleSidebar + Outlet)
  TopNav.tsx            — 顶部导航栏
  ModuleSidebar.tsx     — 左侧子导航 (根据当前模块动态渲染)

frontend/src/pages/v2/
  AssistantPage.tsx     — 包装ChatAgent
  AssistantHistory.tsx  — 包装ChatWithSessions
  OntologyBrowser.tsx   — 包装ObjectExplorer
  OntologyGraph.tsx     — 包装OntologyMap
  DatasourcePage.tsx    — 包装DatasourceManager
  ModelingPage.tsx      — 自动建模 (调scan/infer/confirm API)
  DashboardPage.tsx     — 占位
  AppsPage.tsx          — 占位
  SettingsPage.tsx      — 包装MembersManager
  PipelinesPage.tsx     — 包装PipelineManager
  ApiKeysPage.tsx       — 包装ApiKeyManager
  AuditPage.tsx         — 包装AuditLogViewer
```

### 修改

```
frontend/src/App.tsx    — 添加 /app/* 路由组
```

### 不动

```
frontend/src/pages/*           — 所有现有页面
frontend/src/components/*      — 所有现有组件
frontend/src/services/*        — 所有API服务 (ModelingPage复用现有ontology.ts或新建modeling.ts)
```

## 7. 组件设计

### TopNav

```
高度: 48px
背景: bg-gray-900 border-b border-gray-800
左侧: Logo "Omaha OntoCenter"
中间: 模块tab (AI助手 | 本体 | 看板 | 应用 | 设置)
  未选中: text-gray-400
  选中: text-white border-b-2 border-blue-500
右侧: ProjectSwitcher (复用现有) + 用户头像 dropdown
```

### ModuleSidebar

```
宽度: 200px (AI助手模块下可收起)
背景: bg-gray-900/50 border-r border-gray-800
内容: 当前模块的子页面列表
  未选中: text-gray-400 hover:bg-gray-800
  选中: text-white bg-gray-800
图标: 使用Lucide icons (已有依赖)
```

### AppLayout

```tsx
<div className="h-screen flex flex-col">
  <TopNav />
  <div className="flex flex-1 overflow-hidden">
    <ModuleSidebar />
    <main className="flex-1 overflow-auto bg-gray-950">
      <Outlet />
    </main>
  </div>
</div>
```

### v2 Page Wrapper 模式

```tsx
// 典型的v2 page — 薄wrapper，不复制逻辑
import ObjectExplorer from '../ObjectExplorer';

export default function OntologyBrowser() {
  return <ObjectExplorer />;
}
```

## 8. 视觉风格

保持现有暗色主题，不引入新UI库：
- Tailwind CSS手写TopNav和ModuleSidebar
- 颜色: gray-900/gray-800/gray-950 (与现有一致)
- 选中态: blue-500 accent
- 图标: Lucide (已有依赖)
- 字体/间距: 跟随现有Tailwind配置

## 9. ModelingPage (唯一的新功能页面)

调用Phase 2a的三个API：

```
1. 选择数据源 → POST /scan → 展示表列表
2. 用户勾选表 → POST /infer → 展示推断结果
3. 用户确认 → POST /confirm → 写入DB
```

三步向导式UI，每步一个卡片。这是唯一需要写新逻辑的页面，其他都是wrapper。
