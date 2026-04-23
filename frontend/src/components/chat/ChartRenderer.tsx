import React, { useEffect, useRef } from 'react';

import { useECharts } from '@/hooks/useECharts';

interface ChartRendererProps {
  config: Record<string, any>;
  height?: number;
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({ config, height = 400 }) => {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useECharts(ref);

  useEffect(() => {
    if (!instance.current || !config) return;
    instance.current.setOption(config, { notMerge: true });
  }, [config]);

  return <div ref={ref} style={{ width: '100%', height }} className="mt-2" />;
};
