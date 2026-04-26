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
