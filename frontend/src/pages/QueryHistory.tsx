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
