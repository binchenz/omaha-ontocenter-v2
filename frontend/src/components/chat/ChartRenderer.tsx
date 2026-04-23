import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface ChartRendererProps {
  config: Record<string, any>;
  height?: number;
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({ config, height = 400 }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    instanceRef.current = echarts.init(chartRef.current, 'dark');
    const onResize = () => instanceRef.current?.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      instanceRef.current?.dispose();
    };
  }, []);

  useEffect(() => {
    if (!instanceRef.current || !config) return;
    instanceRef.current.setOption(config, { notMerge: true });
  }, [config]);

  return <div ref={chartRef} style={{ width: '100%', height }} className="mt-2" />;
};
