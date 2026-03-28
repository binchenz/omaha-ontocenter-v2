import React, { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { SemanticObject } from '../../types/semantic';

interface FormulaBuilderProps {
  open: boolean;
  objectName: string;
  objectMeta: SemanticObject | null;
  initialFormula?: string;
  onSave: (formula: string) => void;
  onCancel: () => void;
  onTest: (formula: string) => Promise<{ sql: string | null; error: string | null }>;
}

const OPERATORS = ['+', '-', '*', '/', '>', '<', '>=', '<=', '=', 'AND', 'OR', 'IF(', '(', ')'];

const FormulaBuilder: React.FC<FormulaBuilderProps> = ({
  open, objectName, objectMeta, initialFormula = '', onSave, onCancel, onTest
}) => {
  const [formula, setFormula] = useState(initialFormula);
  const [testResult, setTestResult] = useState<{ sql: string | null; error: string | null } | null>(null);
  const [testing, setTesting] = useState(false);

  const availableFields = objectMeta ? Object.keys(objectMeta.base_properties) : [];

  const appendToFormula = (token: string) => {
    setFormula(prev => prev ? `${prev} ${token}` : token);
    setTestResult(null);
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await onTest(formula);
      setTestResult(result);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={open => { if (!open) onCancel(); }}>
      <DialogContent className="bg-surface border-white/10 text-white max-w-xl">
        <DialogHeader>
          <DialogTitle>公式构建器 — {objectName}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <p className="text-slate-300 text-xs font-medium mb-2">可用字段：</p>
            <div className="flex flex-wrap gap-1">
              {availableFields.map(field => (
                <Badge key={field} variant="secondary"
                  className="cursor-pointer hover:bg-blue-500/30 text-xs"
                  onClick={() => appendToFormula(field)}>
                  {field}
                </Badge>
              ))}
            </div>
          </div>

          <div>
            <p className="text-slate-300 text-xs font-medium mb-2">运算符：</p>
            <div className="flex flex-wrap gap-1">
              {OPERATORS.map(op => (
                <Badge key={op} variant="outline"
                  className="cursor-pointer hover:bg-white/10 text-xs font-mono"
                  onClick={() => appendToFormula(op)}>
                  {op}
                </Badge>
              ))}
            </div>
          </div>

          <div>
            <p className="text-slate-300 text-xs font-medium mb-2">公式：</p>
            <textarea
              value={formula}
              onChange={e => { setFormula(e.target.value); setTestResult(null); }}
              rows={3}
              placeholder="点击字段和运算符构建公式，或直接输入"
              className="w-full rounded-md border border-white/10 bg-background px-3 py-2 text-sm text-white font-mono resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <Button variant="outline" onClick={handleTest} disabled={testing || !formula.trim()}
            className="text-slate-300 border-white/10">
            {testing ? '测试中...' : '测试公式'}
          </Button>

          {testResult && (
            <div className={`rounded-md px-3 py-2 text-xs ${testResult.error ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 'bg-green-500/10 text-green-400 border border-green-500/20'}`}>
              {testResult.error ? testResult.error : `SQL: ${testResult.sql}`}
            </div>
          )}
        </div>

        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={onCancel}>取消</Button>
          <Button onClick={() => onSave(formula)} className="bg-primary hover:bg-primary/90">保存</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default FormulaBuilder;
