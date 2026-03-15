/**
 * ChartRenderer component - renders ECharts visualizations.
 */
import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import { Box } from '@mui/material';

interface ChartRendererProps {
  config: Record<string, any>;
  height?: number;
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({
  config,
  height = 400,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);

  // Initialize chart and register resize listener once on mount
  useEffect(() => {
    if (!chartRef.current) return;

    chartInstanceRef.current = echarts.init(chartRef.current);

    const handleResize = () => { chartInstanceRef.current?.resize(); };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chartInstanceRef.current?.dispose();
      chartInstanceRef.current = null;
    };
  }, []);

  // Update chart options when config changes
  useEffect(() => {
    if (!chartInstanceRef.current || !config) return;
    chartInstanceRef.current.setOption(config, { notMerge: true });
  }, [config]);

  return (
    <Box
      ref={chartRef}
      sx={{ width: '100%', height: `${height}px`, mt: 2 }}
    />
  );
};
