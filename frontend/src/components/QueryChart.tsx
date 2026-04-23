import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

type ChartType = 'bar' | 'line' | 'pie';

interface Props {
  data: Record<string, any>[];
  xField: string;
  yField: string;
  chartType?: ChartType;
  height?: number;
}

const QueryChart: React.FC<Props> = ({ data, xField, yField, chartType = 'bar', height = 300 }) => {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    instance.current = echarts.init(ref.current, 'dark');
    const onResize = () => instance.current?.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      instance.current?.dispose();
    };
  }, []);

  useEffect(() => {
    if (!instance.current || !data.length) return;

    const xValues = data.map(r => String(r[xField] ?? ''));
    const yValues = data.map(r => Number(r[yField]) || 0);

    let option: echarts.EChartsOption;

    if (chartType === 'pie') {
      option = {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
        series: [{
          type: 'pie',
          radius: '65%',
          data: xValues.map((name, i) => ({ name, value: yValues[i] })),
          label: { color: '#94a3b8', fontSize: 11 },
        }],
      };
    } else {
      option = {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        grid: { left: 60, right: 20, top: 20, bottom: 60 },
        xAxis: {
          type: 'category',
          data: xValues,
          axisLabel: { color: '#94a3b8', fontSize: 10, rotate: xValues.length > 8 ? 30 : 0 },
          axisLine: { lineStyle: { color: '#334155' } },
        },
        yAxis: {
          type: 'value',
          axisLabel: { color: '#94a3b8', fontSize: 10 },
          splitLine: { lineStyle: { color: '#1e293b' } },
        },
        series: [{
          type: chartType,
          data: yValues,
          itemStyle: { color: '#2563EB' },
          smooth: chartType === 'line',
        }],
      };
    }

    instance.current.setOption(option, true);
  }, [data, xField, yField, chartType]);

  return <div ref={ref} style={{ width: '100%', height }} />;
};

export default QueryChart;
