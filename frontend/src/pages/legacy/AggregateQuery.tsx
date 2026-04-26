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
