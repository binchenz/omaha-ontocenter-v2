# Frontend Redesign Plan B: Features

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Watchlist page, restructure ProjectDetail to 5 tabs with Query/Aggregate/History sub-tabs and Chat session management, then remove Ant Design.

**Architecture:** Builds on Plan A (Tailwind + shadcn/ui already installed). Migrates remaining pages and adds 4 new feature components. Ant Design removed as final step.

**Tech Stack:** React 18, TypeScript, shadcn/ui, Tailwind CSS, lucide-react, axios

**Spec:** `docs/superpowers/specs/2026-03-29-frontend-redesign-design.md`

---

## Chunk 1: Watchlist Page + Service

### Task 1: Create watchlist service

**Files:**
- Create: `frontend/src/services/watchlist.ts`

- [ ] **Step 1: Create watchlist.ts**

```ts
import axios from 'axios';

const PUBLIC_API = '/api/public/v1';

export interface WatchlistItem {
  id: number;
  ts_code: string;
  note: string | null;
  added_at: string;
}

function getToken(): string | null {
  return localStorage.getItem('public_api_token');
}

function headers() {
  return { Authorization: `Bearer ${getToken()}` };
}

export const watchlistService = {
  list: async (): Promise<WatchlistItem[]> => {
    const res = await axios.get(`${PUBLIC_API}/watchlist`, { headers: headers() });
    return res.data.items;
  },
  add: async (ts_code: string, note?: string): Promise<WatchlistItem> => {
    const res = await axios.post(`${PUBLIC_API}/watchlist`, { ts_code, note }, { headers: headers() });
    return res.data;
  },
  remove: async (id: number): Promise<void> => {
    await axios.delete(`${PUBLIC_API}/watchlist/${id}`, { headers: headers() });
  },
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/watchlist.ts
git commit -m "feat: add watchlist service"
```

---

### Task 2: Create Watchlist page

**Files:**
- Create: `frontend/src/pages/Watchlist.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create Watchlist.tsx**

```tsx
import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { watchlistService, WatchlistItem } from '@/services/watchlist';

const TOKEN_KEY = 'public_api_token';

const Watchlist: React.FC = () => {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [token, setToken] = useState(localStorage.getItem(TOKEN_KEY) || '');
  const [tokenInput, setTokenInput] = useState('');
  const [addOpen, setAddOpen] = useState(false);
  const [tsCode, setTsCode] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState('');

  const hasToken = !!token;

  useEffect(() => {
    if (hasToken) loadItems();
  }, [token]);

  const loadItems = async () => {
    setLoading(true);
    setError('');
    try {
      setItems(await watchlistService.list());
    } catch {
      setError('Failed to load watchlist. Check your API token.');
    } finally {
      setLoading(false);
    }
  };

  const saveToken = () => {
    localStorage.setItem(TOKEN_KEY, tokenInput);
    setToken(tokenInput);
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    await watchlistService.add(tsCode, note || undefined);
    setAddOpen(false);
    setTsCode(''); setNote('');
    loadItems();
  };

  const handleRemove = async (id: number) => {
    if (!window.confirm('Remove from watchlist?')) return;
    await watchlistService.remove(id);
    loadItems();
  };

  if (!hasToken) {
    return (
      <Card className="bg-surface border-white/10 max-w-md mx-auto mt-20">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Star size={18} /> Watchlist
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-slate-400 text-sm">Enter your public API token to access your watchlist.</p>
          <div className="space-y-1">
            <Label className="text-slate-300">API Token</Label>
            <Input value={tokenInput} onChange={e => setTokenInput(e.target.value)}
              placeholder="omaha_..." className="bg-background border-white/10 text-white font-mono text-xs" />
          </div>
          <Button onClick={saveToken} className="bg-primary hover:bg-primary/90 w-full">Save Token</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-surface border-white/10">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-white flex items-center gap-2">
          <Star size={18} /> Watchlist
        </CardTitle>
        <Button onClick={() => setAddOpen(true)} size="sm" className="bg-primary hover:bg-primary/90">
          <Plus size={16} className="mr-2" /> Add Stock
        </Button>
      </CardHeader>
      <CardContent>
        {error && <p className="text-red-400 text-sm mb-4">{error}</p>}
        {loading ? (
          <p className="text-slate-400 text-sm">Loading...</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-white/10">
                <TableHead className="text-slate-400">Code</TableHead>
                <TableHead className="text-slate-400">Note</TableHead>
                <TableHead className="text-slate-400">Added</TableHead>
                <TableHead className="text-slate-400"></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 && (
                <TableRow><TableCell colSpan={4} className="text-slate-400 text-center">No stocks in watchlist</TableCell></TableRow>
              )}
              {items.map(item => (
                <TableRow key={item.id} className="border-white/10 hover:bg-white/5">
                  <TableCell className="text-white font-mono">{item.ts_code}</TableCell>
                  <TableCell className="text-slate-400">{item.note || '—'}</TableCell>
                  <TableCell className="text-slate-400 text-xs font-mono">
                    {new Date(item.added_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => handleRemove(item.id)}
                      className="text-red-400 hover:text-red-300">
                      <Trash2 size={14} />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="bg-surface border-white/10 text-white">
          <DialogHeader><DialogTitle>Add Stock to Watchlist</DialogTitle></DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            <div className="space-y-1">
              <Label className="text-slate-300">Stock Code *</Label>
              <Input value={tsCode} onChange={e => setTsCode(e.target.value)} required
                placeholder="000001.SZ" className="bg-background border-white/10 text-white font-mono" />
            </div>
            <div className="space-y-1">
              <Label className="text-slate-300">Note</Label>
              <Input value={note} onChange={e => setNote(e.target.value)}
                placeholder="Optional note" className="bg-background border-white/10 text-white" />
            </div>
            <div className="flex gap-2 justify-end">
              <Button type="button" variant="ghost" onClick={() => setAddOpen(false)}>Cancel</Button>
              <Button type="submit" className="bg-primary hover:bg-primary/90">Add</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </Card>
  );
};

export default Watchlist;
```

- [ ] **Step 2: Add /watchlist route to App.tsx**

In `frontend/src/App.tsx`, add the import and a top-level route inside the layout `Route` (same level as `projects`, not nested under `projects/:id`):

```tsx
import Watchlist from './pages/Watchlist';

// Inside the layout Route children, alongside <Route path="projects" ...>:
<Route path="watchlist" element={<Watchlist />} />
```

The final route structure should be:
```tsx
<Route path="/" element={<PrivateRoute><MainLayout /></PrivateRoute>}>
  <Route index element={<Navigate to="/projects" replace />} />
  <Route path="projects" element={<ProjectList />} />
  <Route path="projects/:id" element={<ProjectDetail />} />
  <Route path="watchlist" element={<Watchlist />} />   {/* new */}
</Route>
```

Remove the now-unused standalone routes (`projects/:id/explorer`, `projects/:id/assets`, `projects/:projectId/chat`, `projects/:id/semantic`) since these pages are now tabs inside ProjectDetail.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Watchlist.tsx frontend/src/App.tsx
git commit -m "feat: add Watchlist page"
```

---

## Chunk 2: Query History Service + QueryBuilder + AggregateQuery

### Task 3: Create queryHistory service

**Files:**
- Create: `frontend/src/services/queryHistory.ts`

- [ ] **Step 1: Create queryHistory.ts**

```ts
export interface QueryHistoryEntry {
  id: string;
  timestamp: number;
  projectId: number;
  objectType: string;
  filters: Record<string, unknown>;
  resultCount: number;
}

const KEY = 'omaha_query_history';
const MAX = 100;

export const queryHistoryService = {
  list: (projectId: number): QueryHistoryEntry[] => {
    const all: QueryHistoryEntry[] = JSON.parse(localStorage.getItem(KEY) || '[]');
    return all.filter(e => e.projectId === projectId).sort((a, b) => b.timestamp - a.timestamp);
  },
  add: (entry: Omit<QueryHistoryEntry, 'id' | 'timestamp'>) => {
    const all: QueryHistoryEntry[] = JSON.parse(localStorage.getItem(KEY) || '[]');
    all.unshift({ ...entry, id: crypto.randomUUID(), timestamp: Date.now() });
    localStorage.setItem(KEY, JSON.stringify(all.slice(0, MAX)));
  },
  clear: (projectId: number) => {
    const all: QueryHistoryEntry[] = JSON.parse(localStorage.getItem(KEY) || '[]');
    localStorage.setItem(KEY, JSON.stringify(all.filter(e => e.projectId !== projectId)));
  },
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/queryHistory.ts
git commit -m "feat: add query history service (localStorage)"
```

---

### Task 4: Create QueryBuilder component

**Files:**
- Create: `frontend/src/pages/QueryBuilder.tsx`

- [ ] **Step 1: Create QueryBuilder.tsx**

```tsx
import React, { useState } from 'react';
import { Play } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import api from '@/services/api';
import { queryHistoryService } from '@/services/queryHistory';

const OBJECT_TYPES = [
  'Stock','DailyQuote','ValuationMetric','FinancialIndicator',
  'IncomeStatement','BalanceSheet','CashFlow','TechnicalIndicator',
  'Sector','SectorMember',
];

const OPERATORS = ['=', '>', '<', '>=', '<=', 'in'];

interface Filter { field: string; operator: string; value: string; }

interface Props { projectId: number; }

const QueryBuilder: React.FC<Props> = ({ projectId }) => {
  const [objectType, setObjectType] = useState('Stock');
  const [filters, setFilters] = useState<Filter[]>([]);
  const [limit, setLimit] = useState('20');
  const [orderBy, setOrderBy] = useState('');
  const [order, setOrder] = useState('desc');
  const [format, setFormat] = useState(true);
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const addFilter = () => setFilters(f => [...f, { field: '', operator: '=', value: '' }]);
  const removeFilter = (i: number) => setFilters(f => f.filter((_, idx) => idx !== i));
  const updateFilter = (i: number, key: keyof Filter, val: string) =>
    setFilters(f => f.map((item, idx) => idx === i ? { ...item, [key]: val } : item));

  const buildFilters = () => {
    const obj: Record<string, unknown> = {};
    for (const f of filters) {
      if (!f.field) continue;
      if (f.operator === '=') obj[f.field] = f.value;
      else if (f.operator === 'in') obj[f.field] = { operator: 'in', value: f.value.split(',').map(s => s.trim()) };
      else obj[f.field] = { operator: f.operator, value: f.value };
    }
    return obj;
  };

  const handleRun = async () => {
    setLoading(true); setError('');
    try {
      const body: Record<string, unknown> = {
        object_type: objectType,
        filters: buildFilters(),
        limit: parseInt(limit) || 20,
        format,
      };
      if (orderBy) { body.order_by = orderBy; body.order = order; }
      const res = await api.post('/query/public-query', body);
      setResults(res.data.data || []);
      queryHistoryService.add({ projectId, objectType, filters: buildFilters(), resultCount: res.data.count });
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Query failed');
    } finally {
      setLoading(false);
    }
  };

  const columns = results.length > 0 ? Object.keys(results[0]) : [];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <Label className="text-slate-300">Object Type</Label>
          <select value={objectType} onChange={e => setObjectType(e.target.value)}
            className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white">
            {OBJECT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <Label className="text-slate-300">Limit</Label>
          <Input value={limit} onChange={e => setLimit(e.target.value)}
            className="bg-background border-white/10 text-white" />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-slate-300">Filters</Label>
          <Button variant="ghost" size="sm" onClick={addFilter} className="text-primary">+ Add Filter</Button>
        </div>
        {filters.map((f, i) => (
          <div key={i} className="flex gap-2 items-center">
            <Input value={f.field} onChange={e => updateFilter(i, 'field', e.target.value)}
              placeholder="field" className="bg-background border-white/10 text-white flex-1" />
            <select value={f.operator} onChange={e => updateFilter(i, 'operator', e.target.value)}
              className="rounded-md border border-white/10 bg-background px-2 py-2 text-sm text-white">
              {OPERATORS.map(op => <option key={op} value={op}>{op}</option>)}
            </select>
            <Input value={f.value} onChange={e => updateFilter(i, 'value', e.target.value)}
              placeholder="value" className="bg-background border-white/10 text-white flex-1" />
            <Button variant="ghost" size="sm" onClick={() => removeFilter(i)} className="text-red-400">✕</Button>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-1">
          <Label className="text-slate-300">Order By</Label>
          <Input value={orderBy} onChange={e => setOrderBy(e.target.value)}
            placeholder="field name" className="bg-background border-white/10 text-white" />
        </div>
        <div className="space-y-1">
          <Label className="text-slate-300">Order</Label>
          <select value={order} onChange={e => setOrder(e.target.value)}
            className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white">
            <option value="desc">desc</option>
            <option value="asc">asc</option>
          </select>
        </div>
        <div className="space-y-1 flex items-end">
          <label className="flex items-center gap-2 text-sm text-slate-300 pb-2">
            <input type="checkbox" checked={format} onChange={e => setFormat(e.target.checked)} />
            Format output
          </label>
        </div>
      </div>

      <Button onClick={handleRun} disabled={loading} className="bg-primary hover:bg-primary/90">
        <Play size={14} className="mr-2" /> {loading ? 'Running...' : 'Run Query'}
      </Button>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {results.length > 0 && (
        <Card className="bg-background border-white/10 overflow-auto">
          <CardContent className="p-0">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="border-b border-white/10">
                  {columns.map(c => <th key={c} className="px-3 py-2 text-left text-slate-400">{c}</th>)}
                </tr>
              </thead>
              <tbody>
                {results.map((row, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                    {columns.map(c => <td key={c} className="px-3 py-2 text-slate-300">{String(row[c] ?? '')}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default QueryBuilder;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/QueryBuilder.tsx
git commit -m "feat: add QueryBuilder component"
```

---

### Task 5: Create AggregateQuery component

**Files:**
- Create: `frontend/src/pages/AggregateQuery.tsx`

- [ ] **Step 1: Create AggregateQuery.tsx**

```tsx
import React, { useState } from 'react';
import { Play, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent } from '@/components/ui/card';
import api from '@/services/api';

const OBJECT_TYPES = [
  'Stock','DailyQuote','ValuationMetric','FinancialIndicator',
  'IncomeStatement','BalanceSheet','CashFlow','TechnicalIndicator',
];
const AGG_FUNCTIONS = ['count', 'avg', 'max', 'min', 'sum'];

interface Aggregation { field: string; function: string; }

const AggregateQuery: React.FC = () => {
  const [objectType, setObjectType] = useState('DailyQuote');
  const [filterField, setFilterField] = useState('');
  const [filterValue, setFilterValue] = useState('');
  const [aggregations, setAggregations] = useState<Aggregation[]>([{ field: '', function: 'avg' }]);
  const [results, setResults] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const addAgg = () => setAggregations(a => [...a, { field: '', function: 'avg' }]);
  const removeAgg = (i: number) => setAggregations(a => a.filter((_, idx) => idx !== i));
  const updateAgg = (i: number, key: keyof Aggregation, val: string) =>
    setAggregations(a => a.map((item, idx) => idx === i ? { ...item, [key]: val } : item));

  const handleRun = async () => {
    setLoading(true); setError('');
    try {
      const filters: Record<string, unknown> = {};
      if (filterField && filterValue) filters[filterField] = filterValue;
      const res = await api.post('/query/public-aggregate', {
        object_type: objectType,
        filters,
        aggregations: aggregations.filter(a => a.field),
      });
      setResults(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Aggregate query failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <Label className="text-slate-300">Object Type</Label>
        <select value={objectType} onChange={e => setObjectType(e.target.value)}
          className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white">
          {OBJECT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <Label className="text-slate-300">Filter Field (optional)</Label>
          <Input value={filterField} onChange={e => setFilterField(e.target.value)}
            placeholder="e.g. ts_code" className="bg-background border-white/10 text-white" />
        </div>
        <div className="space-y-1">
          <Label className="text-slate-300">Filter Value</Label>
          <Input value={filterValue} onChange={e => setFilterValue(e.target.value)}
            placeholder="e.g. 000001.SZ" className="bg-background border-white/10 text-white" />
        </div>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-slate-300">Aggregations</Label>
          <Button variant="ghost" size="sm" onClick={addAgg} className="text-primary">
            <Plus size={14} className="mr-1" /> Add
          </Button>
        </div>
        {aggregations.map((a, i) => (
          <div key={i} className="flex gap-2 items-center">
            <Input value={a.field} onChange={e => updateAgg(i, 'field', e.target.value)}
              placeholder="field name" className="bg-background border-white/10 text-white flex-1" />
            <select value={a.function} onChange={e => updateAgg(i, 'function', e.target.value)}
              className="rounded-md border border-white/10 bg-background px-2 py-2 text-sm text-white">
              {AGG_FUNCTIONS.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
            <Button variant="ghost" size="sm" onClick={() => removeAgg(i)} className="text-red-400">
              <X size={14} />
            </Button>
          </div>
        ))}
      </div>

      <Button onClick={handleRun} disabled={loading} className="bg-primary hover:bg-primary/90">
        <Play size={14} className="mr-2" /> {loading ? 'Running...' : 'Run Aggregate'}
      </Button>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {results && (
        <Card className="bg-background border-white/10">
          <CardContent className="p-4">
            <pre className="text-xs font-mono text-slate-300 whitespace-pre-wrap">
              {JSON.stringify(results, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AggregateQuery;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AggregateQuery.tsx
git commit -m "feat: add AggregateQuery component"
```

---

### Task 6: Create QueryHistory component

**Files:**
- Create: `frontend/src/pages/QueryHistory.tsx`

- [ ] **Step 1: Create QueryHistory.tsx**

```tsx
import React, { useState, useEffect } from 'react';
import { Trash2, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { queryHistoryService, QueryHistoryEntry } from '@/services/queryHistory';

interface Props { projectId: number; onRerun?: (entry: QueryHistoryEntry) => void; }

const QueryHistory: React.FC<Props> = ({ projectId, onRerun }) => {
  const [entries, setEntries] = useState<QueryHistoryEntry[]>([]);

  useEffect(() => {
    setEntries(queryHistoryService.list(projectId));
  }, [projectId]);

  const handleClear = () => {
    if (!window.confirm('Clear all query history for this project?')) return;
    queryHistoryService.clear(projectId);
    setEntries([]);
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button variant="ghost" size="sm" onClick={handleClear} className="text-red-400 hover:text-red-300">
          <Trash2 size={14} className="mr-2" /> Clear History
        </Button>
      </div>
      {entries.length === 0 ? (
        <p className="text-slate-400 text-sm text-center py-8">No query history yet</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="border-white/10">
              <TableHead className="text-slate-400">Time</TableHead>
              <TableHead className="text-slate-400">Object Type</TableHead>
              <TableHead className="text-slate-400">Filters</TableHead>
              <TableHead className="text-slate-400">Results</TableHead>
              <TableHead className="text-slate-400"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map(e => (
              <TableRow key={e.id} className="border-white/10 hover:bg-white/5">
                <TableCell className="text-slate-400 text-xs font-mono">
                  {new Date(e.timestamp).toLocaleString()}
                </TableCell>
                <TableCell className="text-white text-sm">{e.objectType}</TableCell>
                <TableCell className="text-slate-400 text-xs font-mono max-w-xs truncate">
                  {JSON.stringify(e.filters)}
                </TableCell>
                <TableCell className="text-slate-400 text-sm">{e.resultCount}</TableCell>
                <TableCell>
                  {onRerun && (
                    <Button variant="ghost" size="sm" onClick={() => onRerun(e)} className="text-primary">
                      <RotateCcw size={14} />
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
};

export default QueryHistory;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/QueryHistory.tsx
git commit -m "feat: add QueryHistory component"
```

---

## Chunk 3: ProjectDetail Restructure

### Task 6b: Create ChatWithSessions component

**Files:**
- Create: `frontend/src/pages/ChatWithSessions.tsx`

- [ ] **Step 1: Create ChatWithSessions.tsx**

```tsx
import React, { useState, useEffect } from 'react';
import { Plus, Trash2, MessageSquare } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { chatApi } from '@/services/chatApi';
import { ChatSession } from '@/types';
import { ChatAgent } from './ChatAgent';
import { cn } from '@/lib/utils';

interface Props { projectId: number; }

const ChatWithSessions: React.FC<Props> = ({ projectId }) => {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);

  useEffect(() => { loadSessions(); }, [projectId]);

  const loadSessions = async () => {
    const data = await chatApi.listSessions(projectId);
    setSessions(data);
    if (data.length > 0 && !activeSessionId) setActiveSessionId(data[0].id);
  };

  const handleNew = async () => {
    const session = await chatApi.createSession(projectId, { title: `Session ${sessions.length + 1}` });
    await loadSessions();
    setActiveSessionId(session.id);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Delete this session?')) return;
    await chatApi.deleteSession(projectId, id);
    if (activeSessionId === id) setActiveSessionId(null);
    await loadSessions();
  };

  return (
    <div className="flex h-[600px] border border-white/10 rounded-lg overflow-hidden">
      {/* Session list */}
      <div className="w-48 bg-background border-r border-white/10 flex flex-col">
        <div className="p-3 border-b border-white/10">
          <Button size="sm" onClick={handleNew} className="w-full bg-primary hover:bg-primary/90 text-xs">
            <Plus size={12} className="mr-1" /> New Session
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sessions.map(s => (
            <div
              key={s.id}
              className={cn(
                'flex items-center gap-2 px-3 py-2 cursor-pointer text-xs group',
                activeSessionId === s.id
                  ? 'bg-primary/10 text-primary border-l-2 border-primary'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'
              )}
              onClick={() => setActiveSessionId(s.id)}
            >
              <MessageSquare size={12} className="shrink-0" />
              <span className="flex-1 truncate">{s.title || `Session ${s.id}`}</span>
              <button
                onClick={e => { e.stopPropagation(); handleDelete(s.id); }}
                className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <p className="text-slate-500 text-xs text-center p-4">No sessions yet</p>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-hidden">
        {activeSessionId ? (
          <ChatAgent projectIdProp={projectId} />
        ) : (
          <div className="flex items-center justify-center h-full text-slate-500 text-sm">
            Select or create a session
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatWithSessions;
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/ChatWithSessions.tsx
git commit -m "feat: add ChatWithSessions component with session list sidebar"
```

---

### Task 7: Rewrite ProjectDetail with 5 tabs

**Files:**
- Modify: `frontend/src/pages/ProjectDetail.tsx`

- [ ] **Step 1: Verify existing component interfaces**

Run these to confirm the components exist and check their props:
```bash
grep -n "interface\|Props\|export default\|export const" frontend/src/pages/OntologyViewer.tsx | head -10
grep -n "interface\|Props\|export default\|export const" frontend/src/pages/ObjectExplorer.tsx | head -10
grep -n "interface\|Props\|export default\|export const" frontend/src/pages/AssetList.tsx | head -10
grep -n "interface\|Props\|export default\|export const" frontend/src/pages/ChatAgent.tsx | head -10
grep -n "interface\|Props\|export default\|export const" frontend/src/components/ApiKeyManager.tsx | head -10
```

Confirm:
- `OntologyViewer` accepts `configYaml: string` prop
- `ObjectExplorer` accepts `projectId: number | undefined` prop
- `ChatAgent` is a named export accepting `projectIdProp: number` prop
- `ApiKeyManager` accepts `projectId: number` prop
- `AssetList` accepts no required props

If any prop names differ, adjust the ProjectDetail code in Step 2 accordingly.

- [ ] **Step 2: Rewrite ProjectDetail.tsx**

Replace entire file with shadcn/ui version:

```tsx
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Save, CheckCircle, Key } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import CodeMirror from '@uiw/react-codemirror';
import { yaml } from '@codemirror/lang-yaml';
import { projectService } from '@/services/project';
import { ontologyService } from '@/services/ontology';
import { Project } from '@/types';
import ObjectExplorer from './ObjectExplorer';
import OntologyViewer from './OntologyViewer';
import AssetList from './AssetList';
import ApiKeyManager from '../components/ApiKeyManager';
import ChatWithSessions from './ChatWithSessions';
import QueryBuilder from './QueryBuilder';
import AggregateQuery from './AggregateQuery';
import QueryHistory from './QueryHistory';

const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? parseInt(id) : undefined;
  const [project, setProject] = useState<Project | null>(null);
  const [config, setConfig] = useState('');
  const [loading, setLoading] = useState(false);
  const [apiKeyOpen, setApiKeyOpen] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => { loadProject(); }, [id]);

  const loadProject = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await projectService.get(projectId);
      setProject(data);
      setConfig(data.omaha_config || '');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!projectId) return;
    await projectService.update(projectId, { omaha_config: config });
    setStatusMsg('Saved');
    setTimeout(() => setStatusMsg(''), 2000);
  };

  const handleValidate = async () => {
    const result = await ontologyService.validate(config);
    setStatusMsg(result.valid ? 'Valid' : `Error: ${result.errors.join(', ')}`);
    setTimeout(() => setStatusMsg(''), 3000);
  };

  if (loading && !project) {
    return <div className="text-slate-400 p-6">Loading...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-white text-xl font-semibold">{project?.name}</h1>
        <div className="flex items-center gap-2">
          {statusMsg && (
            <span className="text-sm text-green-400 flex items-center gap-1">
              <CheckCircle size={14} /> {statusMsg}
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={() => setApiKeyOpen(true)} className="text-slate-400">
            <Key size={14} className="mr-2" /> API Keys
          </Button>
          <Button variant="ghost" size="sm" onClick={handleValidate} className="text-slate-400">
            Validate
          </Button>
          <Button size="sm" onClick={handleSave} className="bg-primary hover:bg-primary/90">
            <Save size={14} className="mr-2" /> Save
          </Button>
        </div>
      </div>

      <Tabs defaultValue="config" className="w-full">
        <TabsList className="bg-surface border border-white/10">
          <TabsTrigger value="config" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Config</TabsTrigger>
          <TabsTrigger value="ontology" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Ontology</TabsTrigger>
          <TabsTrigger value="explorer" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Explorer</TabsTrigger>
          <TabsTrigger value="assets" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Assets</TabsTrigger>
          <TabsTrigger value="chat" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Chat</TabsTrigger>
        </TabsList>

        <TabsContent value="config" className="mt-4">
          <CodeMirror
            value={config}
            height="600px"
            extensions={[yaml()]}
            onChange={setConfig}
            theme="dark"
          />
        </TabsContent>

        <TabsContent value="ontology" className="mt-4">
          <OntologyViewer configYaml={config} />
        </TabsContent>

        <TabsContent value="explorer" className="mt-4">
          <Tabs defaultValue="objects">
            <TabsList className="bg-background border border-white/10 mb-4">
              <TabsTrigger value="objects" className="data-[state=active]:text-primary text-sm">Objects</TabsTrigger>
              <TabsTrigger value="query" className="data-[state=active]:text-primary text-sm">Query</TabsTrigger>
              <TabsTrigger value="aggregate" className="data-[state=active]:text-primary text-sm">Aggregate</TabsTrigger>
              <TabsTrigger value="history" className="data-[state=active]:text-primary text-sm">History</TabsTrigger>
            </TabsList>
            <TabsContent value="objects"><ObjectExplorer projectId={projectId} /></TabsContent>
            <TabsContent value="query">{projectId && <QueryBuilder projectId={projectId} />}</TabsContent>
            <TabsContent value="aggregate"><AggregateQuery /></TabsContent>
            <TabsContent value="history">{projectId && <QueryHistory projectId={projectId} />}</TabsContent>
          </Tabs>
        </TabsContent>

        <TabsContent value="assets" className="mt-4">
          <AssetList />
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          {projectId && <ChatWithSessions projectId={projectId} />}
        </TabsContent>
      </Tabs>

      <Dialog open={apiKeyOpen} onOpenChange={setApiKeyOpen}>
        <DialogContent className="bg-surface border-white/10 text-white max-w-2xl">
          <DialogHeader><DialogTitle>API Keys</DialogTitle></DialogHeader>
          {projectId && <ApiKeyManager projectId={projectId} />}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProjectDetail;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ProjectDetail.tsx
git commit -m "feat: restructure ProjectDetail to 5 tabs with query sub-tabs"
```

---

## Chunk 4: Remove Ant Design

### Task 8: Remove Ant Design dependency

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Check for remaining Ant Design imports**

```bash
grep -r "from 'antd'" frontend/src/ --include="*.tsx" --include="*.ts"
grep -r "from '@ant-design" frontend/src/ --include="*.tsx" --include="*.ts"
```

Fix any remaining files that still import from `antd` or `@ant-design/icons` before proceeding.

- [ ] **Step 2: Uninstall Ant Design**

```bash
cd frontend
npm uninstall antd @ant-design/icons
```

- [ ] **Step 3: Remove MUI if unused**

```bash
grep -r "from '@mui" frontend/src/ --include="*.tsx" --include="*.ts"
```

If no results: `npm uninstall @mui/material @mui/icons-material @emotion/react @emotion/styled`

- [ ] **Step 4: Run build to verify no broken imports**

```bash
cd frontend && npm run build 2>&1
```
Expected: build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: remove Ant Design dependency"
```

---

### Task 9: Final verification

- [ ] **Step 1: Run full build**

```bash
cd frontend && npm run build 2>&1
```
Expected: zero errors.

- [ ] **Step 2: Manual smoke test** *(run by human, not agent)*

Run `npm run dev` manually, verify:
- Sidebar navigation works (Projects, Watchlist)
- Login/Register render with dark theme
- ProjectList shows table with dark styling
- ProjectDetail shows 5 tabs; Explorer tab has 4 sub-tabs (Objects, Query, Aggregate, History)
- Chat tab shows session list sidebar on the left
- Watchlist page loads (shows token prompt if no token set)
- No Ant Design styles visible anywhere

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: Plan B complete - all features + Ant Design removed"
```
