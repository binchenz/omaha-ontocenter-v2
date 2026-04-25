interface QualityIssue {
  table: string;
  column: string | null;
  issue_type: string;
  count: number;
  examples: string[];
  suggestion: string;
  auto_fixable: boolean;
}

interface Props {
  data: {
    score: number;
    issues: QualityIssue[];
  };
  onAutoFix?: () => void;
}

const ISSUE_LABELS: Record<string, string> = {
  duplicate_rows: '重复行',
  missing_values: '缺失值',
  inconsistent_format: '格式不一致',
  non_numeric: '非数字内容',
};

function scoreColor(score: number): string {
  if (score >= 90) return 'text-green-400';
  if (score >= 70) return 'text-yellow-400';
  return 'text-red-400';
}

export function QualityPanel({ data, onAutoFix }: Props) {
  const autoFixable = data.issues.filter((i) => i.auto_fixable);
  const needsConfirm = data.issues.filter((i) => !i.auto_fixable);

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-300">数据质量评分</span>
        <span className={`text-2xl font-bold ${scoreColor(data.score)}`}>
          {data.score}/100
        </span>
      </div>

      {data.issues.length === 0 ? (
        <p className="text-sm text-green-400">数据质量良好，无需清洗</p>
      ) : (
        <div className="space-y-2">
          {data.issues.map((issue, i) => (
            <div key={i} className="text-sm border-l-2 border-yellow-500 pl-3 py-1">
              <p className="text-gray-200">
                {ISSUE_LABELS[issue.issue_type] || issue.issue_type}
                {issue.column && ` · ${issue.table}.${issue.column}`}
                {!issue.column && ` · ${issue.table}`}
                <span className="text-gray-400 ml-2">({issue.count} 处)</span>
              </p>
              {issue.examples.length > 0 && (
                <p className="text-gray-500 text-xs mt-0.5">
                  例：{issue.examples.slice(0, 3).join(' / ')}
                </p>
              )}
              <p className="text-gray-400 text-xs">{issue.suggestion}</p>
            </div>
          ))}
        </div>
      )}

      {autoFixable.length > 0 && (
        <button
          onClick={onAutoFix}
          className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm text-white transition-colors"
        >
          一键修复 {autoFixable.length} 个可自动处理的问题
        </button>
      )}

      {needsConfirm.length > 0 && (
        <p className="text-xs text-gray-500">
          还有 {needsConfirm.length} 个问题需要你确认处理方式
        </p>
      )}
    </div>
  );
}
