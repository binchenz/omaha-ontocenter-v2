# Frontend Layout Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new Palantir-style layout (top nav + module sidebar) under `/app/*` routes, coexisting with the old layout. Existing code untouched.

**Architecture:** Three new layout components (TopNav, ModuleSidebar, AppLayout) + thin v2 page wrappers that import existing page components. New `/app/*` route group in App.tsx. Old routes unchanged.

**Tech Stack:** React 18, React Router 6, Tailwind CSS, Lucide icons

**Spec Reference:** `docs/superpowers/specs/2026-04-25-frontend-layout-design.md`

---

## File Structure

### New Files
- `frontend/src/layouts/TopNav.tsx` — Top navigation bar with module tabs
- `frontend/src/layouts/ModuleSidebar.tsx` — Left sidebar with sub-page links
- `frontend/src/layouts/AppLayout.tsx` — Shell combining TopNav + ModuleSidebar + Outlet
- `frontend/src/layouts/navConfig.ts` — Navigation structure data (modules, sub-pages, icons)
- `frontend/src/pages/v2/AssistantPage.tsx` — Wraps ChatWithSessions
- `frontend/src/pages/v2/OntologyBrowser.tsx` — Wraps ObjectExplorer
- `frontend/src/pages/v2/OntologyGraph.tsx` — Wraps OntologyMap
- `frontend/src/pages/v2/DatasourcePage.tsx` — Wraps DatasourceManager
- `frontend/src/pages/v2/ModelingPage.tsx` — New auto-modeling wizard
- `frontend/src/pages/v2/DashboardPage.tsx` — Placeholder
- `frontend/src/pages/v2/AppsPage.tsx` — Placeholder
- `frontend/src/pages/v2/SettingsPage.tsx` — Wraps MembersManager
- `frontend/src/pages/v2/PipelinesPage.tsx` — Wraps PipelineManager
- `frontend/src/pages/v2/ApiKeysPage.tsx` — Wraps ApiKeyManager
- `frontend/src/pages/v2/AuditPage.tsx` — Wraps AuditLogViewer
- `frontend/src/services/modeling.ts` — API client for scan/infer/confirm

### Modified Files
- `frontend/src/App.tsx` — Add `/app/*` route group

---

## Task 1: Navigation Config Data

**Files:**
- Create: `frontend/src/layouts/navConfig.ts`

- [ ] **Step 1: Create navigation config**

```typescript
// frontend/src/layouts/navConfig.ts
import {
  MessageSquare, History, Database, GitBranch, HardDrive, Upload,
  LayoutDashboard, LayoutTemplate, AppWindow,
  Users, Workflow, Key, ClipboardList,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface SubPage {
  label: string;
  path: string;
  icon: LucideIcon;
}

export interface NavModule {
  key: string;
  label: string;
  basePath: string;
  subPages: SubPage[];
}

export const NAV_MODULES: NavModule[] = [
  {
    key: 'assistant',
    label: 'AI助手',
    basePath: '/app/assistant',
    subPages: [
      { label: '对话', path: '/app/assistant', icon: MessageSquare },
      { label: '历史', path: '/app/assistant/history', icon: History },
    ],
  },
  {
    key: 'ontology',
    label: '本体',
    basePath: '/app/ontology',
    subPages: [
      { label: '对象浏览', path: '/app/ontology', icon: Database },
      { label: '关系图谱', path: '/app/ontology/graph', icon: GitBranch },
      { label: '数据源', path: '/app/ontology/datasources', icon: HardDrive },
      { label: '导入/建模', path: '/app/ontology/modeling', icon: Upload },
    ],
  },
  {
    key: 'dashboard',
    label: '看板',
    basePath: '/app/dashboard',
    subPages: [
      { label: '我的看板', path: '/app/dashboard', icon: LayoutDashboard },
      { label: '模板看板', path: '/app/dashboard/templates', icon: LayoutTemplate },
    ],
  },
  {
    key: 'apps',
    label: '应用',
    basePath: '/app/apps',
    subPages: [
      { label: '应用中心', path: '/app/apps', icon: AppWindow },
    ],
  },
  {
    key: 'settings',
    label: '设置',
    basePath: '/app/settings',
    subPages: [
      { label: '成员管理', path: '/app/settings', icon: Users },
      { label: 'Pipeline', path: '/app/settings/pipelines', icon: Workflow },
      { label: 'API密钥', path: '/app/settings/api-keys', icon: Key },
      { label: '审计日志', path: '/app/settings/audit', icon: ClipboardList },
    ],
  },
];

export function findModuleByPath(pathname: string): NavModule | undefined {
  return NAV_MODULES.find((m) => pathname.startsWith(m.basePath));
}
```

- [ ] **Step 2: Verify import**

Run: `cd frontend && npx tsc --noEmit src/layouts/navConfig.ts 2>&1 || echo "Check manually after full build"`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/layouts/navConfig.ts
git commit -m "feat(frontend): add navigation config for new layout"
```

---

## Task 2: TopNav Component

**Files:**
- Create: `frontend/src/layouts/TopNav.tsx`

- [ ] **Step 1: Create TopNav**

```tsx
// frontend/src/layouts/TopNav.tsx
import { useNavigate, useLocation } from 'react-router-dom';
import { NAV_MODULES } from './navConfig';
import { ProjectSwitcher } from '../components/layout/ProjectSwitcher';

export default function TopNav() {
  const navigate = useNavigate();
  const location = useLocation();

  const activeModule = NAV_MODULES.find((m) =>
    location.pathname.startsWith(m.basePath)
  );

  return (
    <header className="h-12 bg-gray-900 border-b border-gray-800 flex items-center px-4 shrink-0">
      <div
        className="text-white font-semibold text-sm mr-8 cursor-pointer"
        onClick={() => navigate('/app/assistant')}
      >
        Omaha OntoCenter
      </div>

      <nav className="flex items-center gap-1 flex-1">
        {NAV_MODULES.map((mod) => {
          const isActive = activeModule?.key === mod.key;
          return (
            <button
              key={mod.key}
              onClick={() => navigate(mod.subPages[0].path)}
              className={`px-3 py-1.5 text-sm rounded transition-colors ${
                isActive
                  ? 'text-white bg-gray-800'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
              }`}
            >
              {mod.label}
            </button>
          );
        })}
      </nav>

      <div className="flex items-center gap-3">
        <ProjectSwitcher />
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/layouts/TopNav.tsx
git commit -m "feat(frontend): add TopNav component with module tabs"
```

---

## Task 3: ModuleSidebar Component

**Files:**
- Create: `frontend/src/layouts/ModuleSidebar.tsx`

- [ ] **Step 1: Create ModuleSidebar**

```tsx
// frontend/src/layouts/ModuleSidebar.tsx
import { useLocation, useNavigate } from 'react-router-dom';
import { findModuleByPath } from './navConfig';

export default function ModuleSidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const currentModule = findModuleByPath(location.pathname);

  if (!currentModule) return null;

  return (
    <aside className="w-50 bg-gray-900/50 border-r border-gray-800 shrink-0 overflow-y-auto">
      <div className="p-3">
        <h2 className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2 px-2">
          {currentModule.label}
        </h2>
        <nav className="flex flex-col gap-0.5">
          {currentModule.subPages.map((page) => {
            const isActive =
              location.pathname === page.path ||
              (page.path !== currentModule.basePath &&
                location.pathname.startsWith(page.path));
            const exactMatch =
              page.path === currentModule.basePath &&
              location.pathname === page.path;
            const active = isActive || exactMatch;

            const Icon = page.icon;
            return (
              <button
                key={page.path}
                onClick={() => navigate(page.path)}
                className={`flex items-center gap-2 px-2 py-1.5 rounded text-sm transition-colors w-full text-left ${
                  active
                    ? 'text-white bg-gray-800'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`}
              >
                <Icon size={16} />
                {page.label}
              </button>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/layouts/ModuleSidebar.tsx
git commit -m "feat(frontend): add ModuleSidebar with dynamic sub-page navigation"
```

---

## Task 4: AppLayout Shell

**Files:**
- Create: `frontend/src/layouts/AppLayout.tsx`

- [ ] **Step 1: Create AppLayout**

```tsx
// frontend/src/layouts/AppLayout.tsx
import { Outlet, Navigate } from 'react-router-dom';
import TopNav from './TopNav';
import ModuleSidebar from './ModuleSidebar';
import { useAuth } from '../hooks/useAuth';
import { useProject } from '../hooks/useProject';
import { RequireProject } from '../components/RequireProject';

export default function AppLayout() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      <TopNav />
      <div className="flex flex-1 overflow-hidden">
        <ModuleSidebar />
        <main className="flex-1 overflow-auto">
          <RequireProject>
            <Outlet />
          </RequireProject>
        </main>
      </div>
    </div>
  );
}
```

Note: If `useAuth` or `RequireProject` don't exist as shown, check the actual imports from the existing codebase. The old `MainLayout` and `PrivateRoute` show the pattern used. Adapt the auth check to match.

- [ ] **Step 2: Verify it renders**

Run: `cd frontend && npm run dev`
Navigate to `http://localhost:5173/app/assistant` — should see TopNav + empty sidebar + empty content area.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/layouts/AppLayout.tsx
git commit -m "feat(frontend): add AppLayout shell (TopNav + ModuleSidebar + Outlet)"
```

---

## Task 5: V2 Page Wrappers

**Files:**
- Create: all files in `frontend/src/pages/v2/`

- [ ] **Step 1: Create all wrapper pages**

```tsx
// frontend/src/pages/v2/AssistantPage.tsx
import ChatWithSessions from '../ChatWithSessions';
export default function AssistantPage() {
  return <ChatWithSessions />;
}
```

```tsx
// frontend/src/pages/v2/OntologyBrowser.tsx
import ObjectExplorer from '../ObjectExplorer';
export default function OntologyBrowser() {
  return <ObjectExplorer />;
}
```

```tsx
// frontend/src/pages/v2/OntologyGraph.tsx
import OntologyMap from '../OntologyMap';
export default function OntologyGraph() {
  return <OntologyMap />;
}
```

```tsx
// frontend/src/pages/v2/DatasourcePage.tsx
import DatasourceManager from '../DatasourceManager';
export default function DatasourcePage() {
  return <DatasourceManager />;
}
```

```tsx
// frontend/src/pages/v2/DashboardPage.tsx
import { LayoutDashboard } from 'lucide-react';
export default function DashboardPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-500">
      <LayoutDashboard size={48} className="mb-4 text-gray-600" />
      <h2 className="text-lg font-medium text-gray-300">数据看板</h2>
      <p className="text-sm mt-2">即将推出 — 从AI对话中"钉"图表到看板</p>
    </div>
  );
}
```

```tsx
// frontend/src/pages/v2/AppsPage.tsx
import { AppWindow } from 'lucide-react';
export default function AppsPage() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-gray-500">
      <AppWindow size={48} className="mb-4 text-gray-600" />
      <h2 className="text-lg font-medium text-gray-300">应用中心</h2>
      <p className="text-sm mt-2">即将推出 — 表单、看板、提醒等轻应用</p>
    </div>
  );
}
```

```tsx
// frontend/src/pages/v2/SettingsPage.tsx
import MembersManager from '../MembersManager';
export default function SettingsPage() {
  return <MembersManager />;
}
```

```tsx
// frontend/src/pages/v2/PipelinesPage.tsx
import PipelineManager from '../PipelineManager';
export default function PipelinesPage() {
  return <PipelineManager />;
}
```

```tsx
// frontend/src/pages/v2/ApiKeysPage.tsx
import ApiKeyManager from '../../components/ApiKeyManager';
export default function ApiKeysPage() {
  return <ApiKeyManager />;
}
```

```tsx
// frontend/src/pages/v2/AuditPage.tsx
import AuditLogViewer from '../AuditLogViewer';
export default function AuditPage() {
  return <AuditLogViewer />;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/v2/
git commit -m "feat(frontend): add v2 page wrappers for new layout"
```

---

## Task 6: Wire Routes in App.tsx

**Files:**
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Add imports and /app route group**

At the top of App.tsx, add imports:

```tsx
import AppLayout from './layouts/AppLayout';
import AssistantPage from './pages/v2/AssistantPage';
import OntologyBrowser from './pages/v2/OntologyBrowser';
import OntologyGraph from './pages/v2/OntologyGraph';
import DatasourcePage from './pages/v2/DatasourcePage';
import ModelingPage from './pages/v2/ModelingPage';
import DashboardPage from './pages/v2/DashboardPage';
import AppsPage from './pages/v2/AppsPage';
import SettingsPage from './pages/v2/SettingsPage';
import PipelinesPage from './pages/v2/PipelinesPage';
import ApiKeysPage from './pages/v2/ApiKeysPage';
import AuditPage from './pages/v2/AuditPage';
```

Inside the `<Routes>`, add BEFORE the existing routes:

```tsx
{/* New v2 layout */}
<Route path="/app" element={<AppLayout />}>
  <Route index element={<Navigate to="/app/assistant" replace />} />
  <Route path="assistant" element={<AssistantPage />} />
  <Route path="assistant/history" element={<AssistantPage />} />
  <Route path="ontology" element={<OntologyBrowser />} />
  <Route path="ontology/graph" element={<OntologyGraph />} />
  <Route path="ontology/datasources" element={<DatasourcePage />} />
  <Route path="ontology/modeling" element={<ModelingPage />} />
  <Route path="dashboard" element={<DashboardPage />} />
  <Route path="dashboard/templates" element={<DashboardPage />} />
  <Route path="apps" element={<AppsPage />} />
  <Route path="settings" element={<SettingsPage />} />
  <Route path="settings/pipelines" element={<PipelinesPage />} />
  <Route path="settings/api-keys" element={<ApiKeysPage />} />
  <Route path="settings/audit" element={<AuditPage />} />
</Route>
```

- [ ] **Step 2: Verify in browser**

Run: `cd frontend && npm run dev`
Navigate to `http://localhost:5173/app/assistant` — should see new layout with TopNav, sidebar, and chat page.
Navigate to `http://localhost:5173/explorer` — should see old layout unchanged.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): wire /app/* routes to new AppLayout"
```

---

## Task 7: ModelingPage — Auto-Modeling Wizard

**Files:**
- Create: `frontend/src/services/modeling.ts`
- Create: `frontend/src/pages/v2/ModelingPage.tsx`

- [ ] **Step 1: Create modeling API service**

```typescript
// frontend/src/services/modeling.ts
import api from './api';

export interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
}

export interface TableSummary {
  name: string;
  row_count: number;
  columns: ColumnInfo[];
  sample_values: Record<string, string[]>;
}

export interface InferredProperty {
  name: string;
  data_type: string;
  semantic_type: string | null;
  description: string;
}

export interface InferredObject {
  name: string;
  source_entity: string;
  description: string;
  business_context: string;
  domain: string;
  datasource_id: string;
  datasource_type: string;
  properties: InferredProperty[];
}

export interface InferredRelationship {
  name: string;
  from_object: string;
  to_object: string;
  relationship_type: string;
  from_field: string;
  to_field: string;
}

export const modelingService = {
  async scan(projectId: number, datasourceId: string) {
    const resp = await api.post(`/ontology-store/${projectId}/scan`, {
      datasource_id: datasourceId,
    });
    return resp.data as { tables: TableSummary[] };
  },

  async infer(projectId: number, datasourceId: string, tables: string[]) {
    const resp = await api.post(`/ontology-store/${projectId}/infer`, {
      datasource_id: datasourceId,
      tables,
    });
    return resp.data as {
      objects: InferredObject[];
      relationships: InferredRelationship[];
      warnings: string[];
    };
  },

  async confirm(projectId: number, objects: InferredObject[], relationships: InferredRelationship[]) {
    const resp = await api.post(`/ontology-store/${projectId}/confirm`, {
      objects,
      relationships,
    });
    return resp.data as {
      objects_created: number;
      objects_updated: number;
      relationships_created: number;
    };
  },
};
```

- [ ] **Step 2: Create ModelingPage**

```tsx
// frontend/src/pages/v2/ModelingPage.tsx
import React, { useState } from 'react';
import { CheckCircle, Loader2, Database, Brain, Save } from 'lucide-react';
import { useProject } from '../../hooks/useProject';
import { modelingService, TableSummary, InferredObject, InferredRelationship } from '../../services/modeling';

type Step = 'scan' | 'infer' | 'confirm' | 'done';

export default function ModelingPage() {
  const { currentProject } = useProject();
  const [step, setStep] = useState<Step>('scan');
  const [datasourceId, setDatasourceId] = useState('');
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set());
  const [objects, setObjects] = useState<InferredObject[]>([]);
  const [relationships, setRelationships] = useState<InferredRelationship[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [result, setResult] = useState<{ objects_created: number; objects_updated: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const projectId = currentProject?.id;

  const handleScan = async () => {
    if (!projectId || !datasourceId) return;
    setLoading(true);
    setError('');
    try {
      const data = await modelingService.scan(projectId, datasourceId);
      setTables(data.tables);
      setSelectedTables(new Set(data.tables.map((t) => t.name)));
      setStep('infer');
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInfer = async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const data = await modelingService.infer(projectId, datasourceId, [...selectedTables]);
      setObjects(data.objects);
      setRelationships(data.relationships);
      setWarnings(data.warnings);
      setStep('confirm');
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const data = await modelingService.confirm(projectId, objects, relationships);
      setResult(data);
      setStep('done');
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleTable = (name: string) => {
    const next = new Set(selectedTables);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setSelectedTables(next);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-semibold text-white mb-6">AI 自动建模</h1>

      {error && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-2 rounded mb-4 text-sm">
          {error}
        </div>
      )}

      {/* Step 1: Scan */}
      <div className={`rounded-lg border p-4 mb-4 ${step === 'scan' ? 'border-blue-600 bg-gray-900' : 'border-gray-800 bg-gray-900/50'}`}>
        <div className="flex items-center gap-2 mb-3">
          <Database size={18} className={step === 'scan' ? 'text-blue-400' : 'text-gray-500'} />
          <h2 className="text-sm font-medium text-gray-200">1. 扫描数据源</h2>
          {step !== 'scan' && <CheckCircle size={16} className="text-green-500 ml-auto" />}
        </div>
        {step === 'scan' && (
          <div className="flex gap-2">
            <input
              className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white"
              placeholder="数据源ID (如 mysql_erp)"
              value={datasourceId}
              onChange={(e) => setDatasourceId(e.target.value)}
            />
            <button
              onClick={handleScan}
              disabled={loading || !datasourceId}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              扫描
            </button>
          </div>
        )}
      </div>

      {/* Step 2: Select & Infer */}
      <div className={`rounded-lg border p-4 mb-4 ${step === 'infer' ? 'border-blue-600 bg-gray-900' : 'border-gray-800 bg-gray-900/50'}`}>
        <div className="flex items-center gap-2 mb-3">
          <Brain size={18} className={step === 'infer' ? 'text-blue-400' : 'text-gray-500'} />
          <h2 className="text-sm font-medium text-gray-200">2. AI 推断</h2>
          {(step === 'confirm' || step === 'done') && <CheckCircle size={16} className="text-green-500 ml-auto" />}
        </div>
        {step === 'infer' && (
          <>
            <div className="max-h-60 overflow-y-auto mb-3">
              {tables.map((t) => (
                <label key={t.name} className="flex items-center gap-2 py-1 px-2 hover:bg-gray-800 rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedTables.has(t.name)}
                    onChange={() => toggleTable(t.name)}
                    className="rounded"
                  />
                  <span className="text-sm text-gray-300">{t.name}</span>
                  <span className="text-xs text-gray-500 ml-auto">{t.row_count} rows, {t.columns.length} cols</span>
                </label>
              ))}
            </div>
            <button
              onClick={handleInfer}
              disabled={loading || selectedTables.size === 0}
              className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              开始推断 ({selectedTables.size} 张表)
            </button>
          </>
        )}
      </div>

      {/* Step 3: Confirm */}
      <div className={`rounded-lg border p-4 mb-4 ${step === 'confirm' ? 'border-blue-600 bg-gray-900' : 'border-gray-800 bg-gray-900/50'}`}>
        <div className="flex items-center gap-2 mb-3">
          <Save size={18} className={step === 'confirm' ? 'text-blue-400' : 'text-gray-500'} />
          <h2 className="text-sm font-medium text-gray-200">3. 确认并保存</h2>
          {step === 'done' && <CheckCircle size={16} className="text-green-500 ml-auto" />}
        </div>
        {step === 'confirm' && (
          <>
            {warnings.length > 0 && (
              <div className="text-yellow-400 text-xs mb-2">
                {warnings.map((w, i) => <div key={i}>{w}</div>)}
              </div>
            )}
            <div className="max-h-60 overflow-y-auto mb-3 space-y-2">
              {objects.map((obj) => (
                <div key={obj.source_entity} className="bg-gray-800 rounded p-3">
                  <div className="text-sm text-white font-medium">{obj.name} <span className="text-gray-500 font-normal">({obj.source_entity})</span></div>
                  <div className="text-xs text-gray-400 mt-1">{obj.description}</div>
                  <div className="text-xs text-gray-500 mt-1">{obj.properties.length} 个字段</div>
                </div>
              ))}
            </div>
            {relationships.length > 0 && (
              <div className="text-xs text-gray-400 mb-3">
                {relationships.length} 个关系已推断
              </div>
            )}
            <button
              onClick={handleConfirm}
              disabled={loading}
              className="px-4 py-1.5 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50 flex items-center gap-1"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              确认保存
            </button>
          </>
        )}
      </div>

      {/* Done */}
      {step === 'done' && result && (
        <div className="bg-green-900/20 border border-green-800 rounded-lg p-4 text-center">
          <CheckCircle size={32} className="text-green-500 mx-auto mb-2" />
          <p className="text-green-300 text-sm">
            建模完成: 创建 {result.objects_created} 个对象，更新 {result.objects_updated} 个对象
          </p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/modeling.ts frontend/src/pages/v2/ModelingPage.tsx
git commit -m "feat(frontend): add ModelingPage wizard and modeling API service"
```

---

## Task 8: Verify Full Flow

- [ ] **Step 1: Start dev servers**

Run backend: `cd backend && uvicorn app.main:app --reload --port 8000`
Run frontend: `cd frontend && npm run dev`

- [ ] **Step 2: Test new layout**

Navigate to `http://localhost:5173/app/assistant`:
- TopNav shows 5 module tabs
- Sidebar shows "对话" and "历史"
- Content area shows chat interface

Click "本体" tab:
- Sidebar shows "对象浏览", "关系图谱", "数据源", "导入/建模"
- Content shows object explorer

Click "看板" tab:
- Shows placeholder page

Click "设置" tab:
- Sidebar shows "成员管理", "Pipeline", "API密钥", "审计日志"

- [ ] **Step 3: Test old layout still works**

Navigate to `http://localhost:5173/explorer`:
- Old sidebar layout, unchanged

- [ ] **Step 4: Build check**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors

- [ ] **Step 5: Commit any fixes**

```bash
git add -A
git commit -m "chore(frontend): frontend layout redesign complete"
```
