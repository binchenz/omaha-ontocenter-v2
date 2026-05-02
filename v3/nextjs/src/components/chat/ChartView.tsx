"use client";

interface OAGResult {
  object_type?: string;
  matched?: Array<{
    id: string;
    properties: Record<string, { value: any; semantic_type: string }>;
  }>;
}

/**
 * Detect if an OAG result is chartable — has matched rows with at least one numeric property.
 */
export function detectChartable(result: any): boolean {
  if (!result?.matched || result.matched.length === 0) return false;
  if (result.matched.length > 100) return false; // skip very large datasets
  if (result.matched.length < 2) return false; // single row not interesting to chart
  const first = result.matched[0];
  if (!first?.properties) return false;
  const numericProps = Object.values(first.properties).filter(
    (p: any) => typeof p.value === "number" || p.semantic_type === "currency" || p.semantic_type === "number"
  );
  return numericProps.length > 0;
}

function formatValue(v: any, semanticType?: string): string {
  if (typeof v === "number") {
    if (semanticType === "currency") return `¥${v.toLocaleString()}`;
    if (semanticType === "percentage") return `${v}%`;
    return v.toLocaleString();
  }
  return String(v);
}

export function ChartView({ result }: { result: OAGResult }) {
  if (!result.matched || result.matched.length === 0) return null;

  const first = result.matched[0];
  const propKeys = Object.keys(first.properties);
  const numericKey = propKeys.find((k) => {
    const v = first.properties[k];
    return typeof v.value === "number" || v.semantic_type === "currency" || v.semantic_type === "number";
  });
  const labelKey = propKeys.find((k) => k !== numericKey) || propKeys[0];
  if (!numericKey) return null;

  const data = result.matched
    .map((m) => ({
      label: String(m.properties[labelKey]?.value ?? m.id),
      value: Number(m.properties[numericKey]?.value) || 0,
      semanticType: m.properties[numericKey]?.semantic_type,
    }))
    .filter((d) => !isNaN(d.value))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  if (data.length === 0) return null;

  const max = Math.max(...data.map((d) => Math.abs(d.value)));

  return (
    <div className="bg-surface border border-gray-200 rounded-lg p-4 mt-2">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium text-text-primary">
          {numericKey} <span className="text-text-secondary">按</span> {labelKey}
        </h3>
        <span className="text-xs text-text-secondary">{data.length} 项</span>
      </div>
      <div className="space-y-2">
        {data.map((d, i) => {
          const width = max > 0 ? (Math.abs(d.value) / max) * 100 : 0;
          return (
            <div key={i} className="flex items-center gap-2">
              <div className="w-24 text-xs text-text-data truncate">{d.label}</div>
              <div className="flex-1 relative h-6 bg-data rounded overflow-hidden">
                <div
                  className="absolute inset-y-0 left-0 bg-accent rounded transition-all duration-500"
                  style={{ width: `${width}%`, opacity: 0.7 + (0.3 * (1 - i / data.length)) }}
                />
                <div className="absolute inset-0 flex items-center px-2 text-xs font-medium text-text-data">
                  {formatValue(d.value, d.semanticType)}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
