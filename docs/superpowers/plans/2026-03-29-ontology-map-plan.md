# Ontology Map Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-screen `/projects/:id/map` page with ECharts ER diagram + Knowledge Graph views, node click detail drawer with sample data, and deep-link from ProjectDetail's Ontology tab.

**Architecture:** New page `OntologyMap.tsx` loads semantic config, flattens relationships into edges, renders either `ERDiagram` or `KnowledgeGraph` via view toggle. Node click opens `NodeDetailDrawer` (sample data from query API). Routing added to `App.tsx`; entry button in `ProjectDetail`; `ObjectExplorer` reads `location.state.preselect` to auto-select object type.

**Tech Stack:** React 18 + TypeScript + ECharts (already installed) + shadcn/ui + Tailwind CSS (OLED Dark theme)

---

## File Structure

**New files:**
- `frontend/src/pages/OntologyMap.tsx` — page shell: data loading, view toggle, edge extraction, `inferNodeType`
- `frontend/src/components/map/ERDiagram.tsx` — ECharts graph layout:none (grid), directed edges with labels
- `frontend/src/components/map/KnowledgeGraph.tsx` — ECharts graph layout:force, draggable nodes
- `frontend/src/components/map/NodeDetailDrawer.tsx` — bottom slide-in drawer, sample data table, navigate to Explorer

**Modified files:**
- `frontend/src/App.tsx:27` — add `<Route path="projects/:id/map" element={<OntologyMap />} />`
- `frontend/src/pages/ProjectDetail.tsx:102-104` — add "查看本体地图" button in Ontology tab
- `frontend/src/pages/ObjectExplorer.tsx:49-58` — read `location.state.preselect` to auto-select object type

---

## Chunk 1: Shared utilities, NodeDetailDrawer, and ObjectExplorer preselect

### Task 1: Create NodeDetailDrawer component

**Files:**
- Create: `frontend/src/components/map/NodeDetailDrawer.tsx`

**UX requirements for this component (must verify in the code):**
- Animation: `transform: translateY(0/100%)` — never use `height` or `max-height` for the slide-in/out
- Transition: `250ms cubic-bezier(0,0,0.2,1)`
- ESC key: `keydown` listener on `window` calls `onClose()`
- Skeleton: exactly 3 rows while loading (`[1, 2, 3].map(...)`)
- Sample data query: first 5 columns only (`res.columns.slice(0, 5)`), limit = 3 rows
- "前往 Explorer" button must navigate to `/projects/${projectId}/explorer` with `{ state: { preselect: objectName } }`
- Close button must have `focus:ring-2 focus:ring-primary` for keyboard-nav (Enter triggers `onClick`)

- [ ] **Step 1: Write the component**

```tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { queryService } from '@/services/query';

interface NodeDetailDrawerProps {
  projectId: number;
  objectName: string | null;
  fieldCount: number;
  onClose: () => void;
}

const NodeDetailDrawer: React.FC<NodeDetailDrawerProps> = ({
  projectId, objectName, fieldCount, onClose
}) => {
  const navigate = useNavigate();
  const [sampleData, setSampleData] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  useEffect(() => {
    if (!objectName) return;
    setLoading(true);
    setSampleData([]);
    // First fetch schema to get column names (max 5 base properties)
    queryService.getObjectSchema(projectId, objectName)
      .then(res => {
        if (res.success && res.columns) {
          const cols = res.columns.slice(0, 5).map((c: any) => c.name);
          setColumns(cols);
          return queryService.queryObjects(projectId, objectName, cols, [], undefined, 3);
        }
      })
      .then(res => { if (res?.success && res.data) setSampleData(res.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId, objectName]);

  const open = !!objectName;

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 bg-surface border-t border-white/10"
      style={{
        transform: open ? 'translateY(0)' : 'translateY(100%)',
        transition: 'transform 250ms cubic-bezier(0,0,0.2,1)',
        height: '280px',
      }}
      role="dialog"
      aria-modal="true"
      aria-label={objectName ? `${objectName} details` : 'Node details'}
    >
      {objectName && (
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
            <span className="text-white font-medium text-sm">
              {objectName}
              <span className="text-slate-400 ml-2 text-xs">{fieldCount} 个字段</span>
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="text-primary text-xs h-7"
                onClick={() => navigate(`/projects/${projectId}/explorer`, { state: { preselect: objectName } })}
              >
                <ArrowRight size={13} className="mr-1" /> 前往 Explorer
              </Button>
              <button
                onClick={onClose}
                className="text-slate-400 hover:text-white p-1 rounded focus:outline-none focus:ring-2 focus:ring-primary"
                aria-label="关闭"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Sample data */}
          <div className="flex-1 overflow-auto p-4">
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-6 rounded bg-white/5 animate-pulse" />
                ))}
              </div>
            ) : sampleData.length > 0 ? (
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-white/10">
                    {columns.map(c => (
                      <th key={c} className="px-3 py-1.5 text-left text-slate-400">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sampleData.map((row, i) => (
                    <tr key={i} className="border-b border-white/5">
                      {columns.map(c => (
                        <td key={c} className="px-3 py-1.5 text-slate-300">{String(row[c] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-slate-500 text-xs">暂无样本数据</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NodeDetailDrawer;
```

- [ ] **Step 2: Verify TypeScript compiles (no build errors)**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/frontend && npm run build 2>&1 | head -40`
Expected: No TypeScript errors in the new file (other errors unrelated to this file are OK at this stage).

- [ ] **Step 3: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git add frontend/src/components/map/NodeDetailDrawer.tsx
git commit -m "feat: add NodeDetailDrawer component for ontology map"
```

---

### Task 2: Add preselect support to ObjectExplorer

**Files:**
- Modify: `frontend/src/pages/ObjectExplorer.tsx:49-58`

The file already reads `location.state.assetConfig`. We need to also read `location.state.preselect` (a string) and call `setSelectedType` when objectTypes have loaded.

- [ ] **Step 1: Update the location.state effect**

Find the existing `useEffect` at line 49-58:
```tsx
  useEffect(() => {
    const state = location.state as { assetConfig?: any };
    if (state?.assetConfig) {
      const config = state.assetConfig;
      setSelectedType(config.object_type);
      if (config.selected_columns) setSelectedColumns(config.selected_columns);
      if (config.filters) setFilters(config.filters);
      if (config.joins) setJoins(config.joins.map((j: any) => ({ ...j, relationship: {} as Relationship })));
    }
  }, [location.state]);
```

Replace with:
```tsx
  useEffect(() => {
    const state = location.state as { assetConfig?: any; preselect?: string };
    if (state?.assetConfig) {
      const config = state.assetConfig;
      setSelectedType(config.object_type);
      if (config.selected_columns) setSelectedColumns(config.selected_columns);
      if (config.filters) setFilters(config.filters);
      if (config.joins) setJoins(config.joins.map((j: any) => ({ ...j, relationship: {} as Relationship })));
    } else if (state?.preselect) {
      setSelectedType(state.preselect);
    }
  }, [location.state]);
```

- [ ] **Step 2: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git add frontend/src/pages/ObjectExplorer.tsx
git commit -m "feat: support preselect object type in ObjectExplorer via location.state"
```

---

## Chunk 2: ERDiagram and KnowledgeGraph components

### Task 3: Create ERDiagram component

**Files:**
- Create: `frontend/src/components/map/ERDiagram.tsx`

- [ ] **Step 1: Write the component**

```tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface Edge {
  source: string;
  target: string;
  label: string;
}

interface NodeInfo {
  name: string;
  fieldCount: number;
  color: string;
  nodeType: string;
}

interface ERDiagramProps {
  nodes: NodeInfo[];
  edges: Edge[];
  selectedNode: string | null;
  onNodeClick: (name: string) => void;
}

const ERDiagram: React.FC<ERDiagramProps> = ({ nodes, edges, selectedNode, onNodeClick }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    instanceRef.current = echarts.init(chartRef.current, 'dark');

    const COLS = 3;
    const COL_GAP = 280;
    const ROW_GAP = 200;

    const chartNodes = nodes.map((n, i) => ({
      id: n.name,
      name: n.name,
      x: (i % COLS) * COL_GAP,
      y: Math.floor(i / COLS) * ROW_GAP,
      symbol: 'roundRect',
      symbolSize: [160, 60],
      itemStyle: { color: n.color, borderRadius: 8 },
      label: {
        show: true,
        formatter: `{a|${n.name}}\n{b|${n.fieldCount} 个字段}`,
        rich: {
          a: { color: '#fff', fontSize: 12, fontWeight: 600 },
          b: { color: '#94a3b8', fontSize: 10 },
        },
      },
      emphasis: {
        itemStyle: { shadowBlur: 12, shadowColor: n.color },
      },
      cursor: 'pointer',
    }));

    const chartEdges = edges.map(e => ({
      source: e.source,
      target: e.target,
      label: { show: true, formatter: e.label, fontSize: 10, color: '#64748b' },
      lineStyle: { color: '#334155', width: 1.5, curveness: 0.1 },
    }));

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animationDurationUpdate: 150,
      series: [{
        type: 'graph',
        layout: 'none',
        data: chartNodes,
        edges: chartEdges,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        roam: true,
        zoom: 0.9,
        cursor: 'pointer',
        lineStyle: { color: '#334155' },
      }],
    };

    instanceRef.current.setOption(option);
    instanceRef.current.on('click', 'series', (params: any) => {
      if (params.dataType === 'node') onNodeClick(params.name);
    });

    const resizeObserver = new ResizeObserver(() => instanceRef.current?.resize());
    resizeObserver.observe(chartRef.current);

    return () => {
      resizeObserver.disconnect();
      instanceRef.current?.dispose();
      instanceRef.current = null;
    };
  }, [nodes, edges]);

  // Highlight selected node without re-init
  useEffect(() => {
    if (!instanceRef.current) return;
    if (selectedNode) {
      instanceRef.current.dispatchAction({ type: 'highlight', seriesIndex: 0, name: selectedNode });
      instanceRef.current.dispatchAction({ type: 'showTip', seriesIndex: 0, name: selectedNode });
    }
  }, [selectedNode]);

  return (
    <div
      ref={chartRef}
      style={{ width: '100%', height: '100%' }}
      aria-label="ER 图"
    />
  );
};

export default ERDiagram;
```

- [ ] **Step 2: Verify UX rules in code before committing**

Check that the written code contains:
- `animationDurationUpdate: 150` — press-feedback timing
- `symbolSize: [160, 60]` — touch targets ≥ 44px wide/tall
- `cursor: 'pointer'` in series options
- `silent: false` is the default (do NOT set `silent: true`)
- Tooltip set up: edge labels show relationship name (color-not-only rule: text labels on edges)

- [ ] **Step 3: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git add frontend/src/components/map/ERDiagram.tsx
git commit -m "feat: add ERDiagram component with ECharts grid layout"
```

---

### Task 4: Create KnowledgeGraph component

**Files:**
- Create: `frontend/src/components/map/KnowledgeGraph.tsx`

- [ ] **Step 1: Write the component**

```tsx
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface Edge {
  source: string;
  target: string;
  label: string;
}

interface NodeInfo {
  name: string;
  fieldCount: number;
  color: string;
  nodeType: string;
}

interface KnowledgeGraphProps {
  nodes: NodeInfo[];
  edges: Edge[];
  selectedNode: string | null;
  onNodeClick: (name: string) => void;
  projectId: number; // used to reset on project change
}

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  nodes, edges, selectedNode, onNodeClick, projectId
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Dispose previous instance on projectId change to prevent memory leaks
    if (instanceRef.current) {
      instanceRef.current.dispose();
      instanceRef.current = null;
    }

    instanceRef.current = echarts.init(chartRef.current, 'dark');

    const chartNodes = nodes.map(n => ({
      id: n.name,
      name: n.name,
      symbolSize: Math.min(40 + n.fieldCount * 2, 80),
      itemStyle: { color: n.color },
      label: { show: true, color: '#fff', fontSize: 11 },
      emphasis: {
        itemStyle: { shadowBlur: 16, shadowColor: n.color },
      },
      cursor: 'pointer',
      draggable: true,
    }));

    const chartEdges = edges.map(e => ({
      source: e.source,
      target: e.target,
      label: { show: true, formatter: e.label, fontSize: 9, color: '#64748b' },
      lineStyle: { color: '#334155', width: 1, curveness: 0.15 },
    }));

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: !prefersReducedMotion,
      animationDuration: prefersReducedMotion ? 0 : 300,
      series: [{
        type: 'graph',
        layout: 'force',
        data: chartNodes,
        edges: chartEdges,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 6],
        roam: true,
        draggable: true,
        cursor: 'pointer',
        force: {
          repulsion: 300,
          edgeLength: [120, 200],
          gravity: 0.1,
        },
        lineStyle: { color: '#334155' },
      }],
    };

    instanceRef.current.setOption(option);
    instanceRef.current.on('click', 'series', (params: any) => {
      if (params.dataType === 'node') onNodeClick(params.name);
    });

    const resizeObserver = new ResizeObserver(() => instanceRef.current?.resize());
    resizeObserver.observe(chartRef.current);

    return () => {
      resizeObserver.disconnect();
      instanceRef.current?.dispose();
      instanceRef.current = null;
    };
  }, [nodes, edges, projectId]);

  // Highlight selected node
  useEffect(() => {
    if (!instanceRef.current || !selectedNode) return;
    instanceRef.current.dispatchAction({ type: 'highlight', seriesIndex: 0, name: selectedNode });
  }, [selectedNode]);

  return (
    <div
      ref={chartRef}
      style={{ width: '100%', height: '100%' }}
      aria-label="知识图谱"
    />
  );
};

export default KnowledgeGraph;
```

- [ ] **Step 2: Verify UX rules in code before committing**

Check that the written code contains:
- `animation: !prefersReducedMotion` — reduced-motion support
- `cursor: 'pointer'` in series options
- `draggable: true` on each node AND in series options
- `symbolSize: Math.min(40 + n.fieldCount * 2, 80)` — minimum 40dp (touch-friendly)
- dispose-then-reinit pattern triggered by `projectId` in the `useEffect` dep array

- [ ] **Step 3: Verify view-switch continuity**

The OntologyMap page's `handleViewSwitch` must:
1. Save `selectedNode` before calling `setView`
2. After switching view, call `setTimeout(() => setSelectedNode(prev), 50)` to re-apply highlight to new chart instance

Verify this exists in `OntologyMap.tsx`'s `handleViewSwitch` function.

- [ ] **Step 4: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git add frontend/src/components/map/KnowledgeGraph.tsx
git commit -m "feat: add KnowledgeGraph component with ECharts force layout"
```

---

## Chunk 3: OntologyMap page and routing integration

### Task 5: Create OntologyMap page

**Files:**
- Create: `frontend/src/pages/OntologyMap.tsx`

- [ ] **Step 1: Write the page component**

```tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { semanticApi } from '@/services/semanticApi';
import ERDiagram from '../components/map/ERDiagram';
import KnowledgeGraph from '../components/map/KnowledgeGraph';
import NodeDetailDrawer from '../components/map/NodeDetailDrawer';

type ViewMode = 'er' | 'kg';

interface NodeInfo {
  name: string;
  fieldCount: number;
  color: string;
  nodeType: string;
}

interface Edge {
  source: string;
  target: string;
  label: string;
}

function inferNodeType(name: string): 'quote' | 'financial' | 'computed' | 'core' {
  const n = name.toLowerCase();
  if (/quote|daily|price|行情/.test(n)) return 'quote';
  if (/financial|indicator|财务|fina/.test(n)) return 'financial';
  if (/technical|computed|技术|calc/.test(n)) return 'computed';
  return 'core';
}

const NODE_COLORS: Record<string, string> = {
  quote: '#16a34a',
  financial: '#d97706',
  computed: '#7c3aed',
  core: '#2563EB',
};

const OntologyMap: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? parseInt(id) : 0;
  const navigate = useNavigate();

  const [view, setView] = useState<ViewMode>('er');
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [projectName, setProjectName] = useState('');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadOntology();
  }, [projectId]);

  const loadOntology = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await semanticApi.get(projectId);
      const objects = data.parsed?.objects || {};

      const builtNodes: NodeInfo[] = Object.entries(objects).map(([name, obj]: [string, any]) => {
        const nodeType = inferNodeType(name);
        return {
          name,
          fieldCount: Object.keys(obj.base_properties || {}).length,
          color: NODE_COLORS[nodeType],
          nodeType,
        };
      });

      const builtEdges: Edge[] = Object.entries(objects).flatMap(([objName, obj]: [string, any]) =>
        (obj.relationships || [])
          .filter((r: any) => r.from_object === objName)
          .map((r: any) => ({ source: r.from_object, target: r.to_object, label: r.name }))
      );

      setNodes(builtNodes);
      setEdges(builtEdges);
      // Attempt to get project name from any available field
      setProjectName(data.project_name || `项目 ${projectId}`);
    } catch {
      setError('加载本体配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (name: string) => {
    setSelectedNode(prev => prev === name ? null : name);
  };

  const handleViewSwitch = (newView: ViewMode) => {
    const prev = selectedNode;
    setView(newView);
    // Continuity: keep the same node selected after switch
    if (prev) setTimeout(() => setSelectedNode(prev), 50);
  };

  const selectedNodeInfo = nodes.find(n => n.name === selectedNode) || null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      {/* Top bar — 48px */}
      <div
        className="flex items-center justify-between px-4 border-b border-white/10 bg-surface shrink-0"
        style={{ height: 48 }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/projects/${projectId}`)}
            className="text-slate-400 hover:text-white flex items-center gap-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary rounded"
          >
            <ArrowLeft size={15} /> 返回项目
          </button>
          <span className="text-white/30 text-sm">|</span>
          <span className="text-white text-sm font-medium">{projectName} 本体地图</span>
        </div>

        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant={view === 'er' ? 'default' : 'ghost'}
            className={`h-7 text-xs ${view === 'er' ? 'bg-primary text-white' : 'text-slate-400'}`}
            onClick={() => handleViewSwitch('er')}
          >
            ER 图
          </Button>
          <Button
            size="sm"
            variant={view === 'kg' ? 'default' : 'ghost'}
            className={`h-7 text-xs ${view === 'kg' ? 'bg-primary text-white' : 'text-slate-400'}`}
            onClick={() => handleViewSwitch('kg')}
          >
            知识图谱
          </Button>
        </div>
      </div>

      {/* Chart area */}
      <div className="flex-1 relative" style={{ minHeight: 0 }}>
        <div style={{ width: '100%', height: '100%' }}>
          {view === 'er' ? (
            <ERDiagram
              nodes={nodes}
              edges={edges}
              selectedNode={selectedNode}
              onNodeClick={handleNodeClick}
            />
          ) : (
            <KnowledgeGraph
              nodes={nodes}
              edges={edges}
              selectedNode={selectedNode}
              onNodeClick={handleNodeClick}
              projectId={projectId}
            />
          )}
        </div>

        {/* Drawer backdrop dimming when open */}
        {selectedNode && (
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: 'rgba(0,0,0,0.2)' }}
          />
        )}
      </div>

      {/* Detail drawer */}
      <NodeDetailDrawer
        projectId={projectId}
        objectName={selectedNode}
        fieldCount={selectedNodeInfo?.fieldCount ?? 0}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
};

export default OntologyMap;
```

- [ ] **Step 2: Verify these critical requirements in the code**

**inferNodeType function** — must use this exact regex sequence (copied from spec):
```ts
function inferNodeType(name: string): 'quote' | 'financial' | 'computed' | 'core' {
  const n = name.toLowerCase();
  if (/quote|daily|price|行情/.test(n)) return 'quote';
  if (/financial|indicator|财务|fina/.test(n)) return 'financial';
  if (/technical|computed|技术|calc/.test(n)) return 'computed';
  return 'core';
}
```

**Edge deduplication** — must use `.filter(r => r.from_object === objName)` (not `r.to_object`):
```ts
const builtEdges = Object.entries(objects).flatMap(([objName, obj]) =>
  (obj.relationships || [])
    .filter((r: any) => r.from_object === objName)  // ← deduplicate by taking 'from' side only
    .map((r: any) => ({ source: r.from_object, target: r.to_object, label: r.name }))
);
```

**Top-bar buttons keyboard nav** — both "ER 图" and "知识图谱" buttons must be Tab-focusable. Using shadcn `<Button>` ensures this. Verify neither has `tabIndex={-1}`.

- [ ] **Step 3: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git add frontend/src/pages/OntologyMap.tsx
git commit -m "feat: add OntologyMap page with ER/KG view toggle and node drawer"
```

---

### Task 6: Add route, entry button, and wire everything together

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/ProjectDetail.tsx`

- [ ] **Step 1: Add OntologyMap route to App.tsx**

In `frontend/src/App.tsx`, add the import at the top with other page imports:
```tsx
import OntologyMap from './pages/OntologyMap';
```

Add route after the `projects/:id` route (inside the `<Route path="/">` children, before the closing tag):
```tsx
<Route path="projects/:id/map" element={<OntologyMap />} />
```

The full routes block after edit:
```tsx
          <Route index element={<Navigate to="/projects" replace />} />
          <Route path="projects" element={<ProjectList />} />
          <Route path="projects/:id" element={<ProjectDetail />} />
          <Route path="projects/:id/map" element={<OntologyMap />} />
          <Route path="watchlist" element={<Watchlist />} />
```

- [ ] **Step 2: Add "查看本体地图" button to ProjectDetail Ontology tab**

In `frontend/src/pages/ProjectDetail.tsx`, add `useNavigate` to the existing `useParams` import line:
```tsx
import { useParams, useNavigate } from 'react-router-dom';
```

Add `const navigate = useNavigate();` after the existing state declarations (e.g., after `const [statusMsg, setStatusMsg] = useState('');`).

Find the Ontology tab content:
```tsx
        <TabsContent value="ontology" className="mt-4">
          <OntologyViewer configYaml={config} />
        </TabsContent>
```

Replace with:
```tsx
        <TabsContent value="ontology" className="mt-4">
          <div className="flex justify-end mb-3">
            <Button
              size="sm"
              variant="ghost"
              className="text-primary text-xs"
              onClick={() => navigate(`/projects/${projectId}/map`)}
            >
              查看本体地图
            </Button>
          </div>
          <OntologyViewer configYaml={config} />
        </TabsContent>
```

- [ ] **Step 3: Full build check**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/frontend && npm run build 2>&1 | tail -20`
Expected: Build succeeds with no TypeScript errors. Fix any type errors before proceeding.

- [ ] **Step 4: Commit all routing changes**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git add frontend/src/App.tsx frontend/src/pages/ProjectDetail.tsx
git commit -m "feat: wire OntologyMap route and entry button in ProjectDetail"
```

---

### Task 7: Smoke test in browser

- [ ] **Step 1: Start dev server**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/frontend && npm run dev`

- [ ] **Step 2: Verify in browser**

Manual checks:
1. Open a project → Ontology tab → "查看本体地图" button is visible
2. Click button → navigates to `/projects/:id/map`
3. ER diagram renders nodes and edges
4. Toggle to 知识图谱 → force layout renders, nodes are draggable
5. Click a node → bottom drawer slides in with skeleton then sample data
6. Press ESC → drawer closes
7. "前往 Explorer" in drawer → ObjectExplorer loads with the correct object type pre-selected
8. "← 返回项目" → navigates back to project detail

- [ ] **Step 3: Fix any runtime issues found during smoke test**

- [ ] **Step 4: Final commit if fixes were needed**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git add -p  # stage only relevant changes
git commit -m "fix: resolve ontology map smoke test issues"
```
