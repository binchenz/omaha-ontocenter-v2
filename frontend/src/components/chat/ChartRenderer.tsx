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

  useEffect(() => {
    if (!chartRef.current || !config) return;

    // Initialize chart
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current);
    }

    // Set chart options
    chartInstanceRef.current.setOption(config);

    // Handle resize
    const handleResize = () => {
      chartInstanceRef.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [config]);

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      chartInstanceRef.current?.dispose();
      chartInstanceRef.current = null;
    };
  }, []);

  return (
    <Box
      ref={chartRef}
      sx={{
        width: '100%',
        height: `${height}px`,
        mt: 2,
      }}
    />
  );
};
