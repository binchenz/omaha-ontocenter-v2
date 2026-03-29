import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';

interface Edge {
  source: string;
  target: string;
  label: string;
}

interface NodeInfo {
  name: string;
  fieldCount: number;
  color: string;
  nodeType: string;
}

interface ERDiagramProps {
  nodes: NodeInfo[];
  edges: Edge[];
  selectedNode: string | null;
  onNodeClick: (name: string) => void;
}

const ERDiagram: React.FC<ERDiagramProps> = ({ nodes, edges, selectedNode, onNodeClick }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    instanceRef.current = echarts.init(chartRef.current, 'dark');

    const COLS = 3;
    const COL_GAP = 280;
    const ROW_GAP = 200;

    const chartNodes = nodes.map((n, i) => ({
      id: n.name,
      name: n.name,
      x: (i % COLS) * COL_GAP,
      y: Math.floor(i / COLS) * ROW_GAP,
      symbol: 'roundRect',
      symbolSize: [160, 60],
      itemStyle: { color: n.color, borderRadius: 8 },
      label: {
        show: true,
        formatter: `{a|${n.name}}\n{b|${n.fieldCount} 个字段}`,
        rich: {
          a: { color: '#fff', fontSize: 12, fontWeight: 600 },
          b: { color: '#94a3b8', fontSize: 10 },
        },
      },
      emphasis: {
        itemStyle: { shadowBlur: 12, shadowColor: n.color },
      },
      cursor: 'pointer',
    }));

    const chartEdges = edges.map(e => ({
      source: e.source,
      target: e.target,
      label: { show: true, formatter: e.label, fontSize: 10, color: '#64748b' },
      lineStyle: { color: '#334155', width: 1.5, curveness: 0.1 },
    }));

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animationDurationUpdate: 150,
      series: [{
        type: 'graph',
        layout: 'none',
        data: chartNodes,
        edges: chartEdges,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        roam: true,
        zoom: 0.9,
        cursor: 'pointer',
        lineStyle: { color: '#334155' },
      }],
    };

    instanceRef.current.setOption(option);
    instanceRef.current.on('click', 'series', (params: any) => {
      if (params.dataType === 'node') onNodeClick(params.name);
    });

    const resizeObserver = new ResizeObserver(() => instanceRef.current?.resize());
    resizeObserver.observe(chartRef.current);

    return () => {
      resizeObserver.disconnect();
      instanceRef.current?.dispose();
      instanceRef.current = null;
    };
  }, [nodes, edges]);

  // Highlight selected node without re-init
  useEffect(() => {
    if (!instanceRef.current) return;
    if (selectedNode) {
      instanceRef.current.dispatchAction({ type: 'highlight', seriesIndex: 0, name: selectedNode });
      instanceRef.current.dispatchAction({ type: 'showTip', seriesIndex: 0, name: selectedNode });
    }
  }, [selectedNode]);

  return (
    <div
      ref={chartRef}
      style={{ width: '100%', height: '100%' }}
      aria-label="ER 图"
    />
  );
};

export default ERDiagram;
