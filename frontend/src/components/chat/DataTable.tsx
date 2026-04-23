import React from 'react';

interface DataTableProps {
  data: Record<string, any>[];
}

export const DataTable: React.FC<DataTableProps> = ({ data }) => {
  if (!data || data.length === 0) {
    return <p className="text-slate-400 text-sm">暂无数据</p>;
  }

  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-auto max-h-80 rounded border border-white/10 mt-2">
      <table className="w-full text-xs font-mono">
        <thead className="sticky top-0 bg-surface">
          <tr className="border-b border-white/10">
            {columns.map(c => (
              <th key={c} className="px-3 py-2 text-left text-slate-400 font-medium">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b border-white/5 hover:bg-white/5">
              {columns.map(c => (
                <td key={c} className="px-3 py-1.5 text-slate-300">
                  {row[c] !== null && row[c] !== undefined ? String(row[c]) : '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
