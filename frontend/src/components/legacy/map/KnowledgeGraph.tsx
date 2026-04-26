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

interface KnowledgeGraphProps {
  nodes: NodeInfo[];
  edges: Edge[];
  selectedNode: string | null;
  onNodeClick: (name: string) => void;
  projectId: number; // used to reset on project change
}

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({
  nodes, edges, selectedNode, onNodeClick, projectId
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Dispose previous instance on projectId change to prevent memory leaks
    if (instanceRef.current) {
      instanceRef.current.dispose();
      instanceRef.current = null;
    }

    instanceRef.current = echarts.init(chartRef.current, 'dark');

    const chartNodes = nodes.map(n => ({
      id: n.name,
      name: n.name,
      symbolSize: Math.min(40 + n.fieldCount * 2, 80),
      itemStyle: { color: n.color },
      label: { show: true, color: '#fff', fontSize: 11 },
      emphasis: {
        itemStyle: { shadowBlur: 16, shadowColor: n.color },
      },
      cursor: 'pointer',
      draggable: true,
    }));

    const chartEdges = edges.map(e => ({
      source: e.source,
      target: e.target,
      label: { show: true, formatter: e.label, fontSize: 9, color: '#64748b' },
      lineStyle: { color: '#334155', width: 1, curveness: 0.15 },
    }));

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const option: echarts.EChartsOption = {
      backgroundColor: 'transparent',
      animation: !prefersReducedMotion,
      animationDuration: prefersReducedMotion ? 0 : 300,
      series: [{
        type: 'graph',
        layout: 'force',
        data: chartNodes,
        edges: chartEdges,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 6],
        roam: true,
        draggable: true,
        cursor: 'pointer',
        force: {
          repulsion: 300,
          edgeLength: [120, 200],
          gravity: 0.1,
        },
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
  }, [nodes, edges, projectId]);

  // Highlight selected node
  useEffect(() => {
    if (!instanceRef.current || !selectedNode) return;
    instanceRef.current.dispatchAction({ type: 'highlight', seriesIndex: 0, name: selectedNode });
  }, [selectedNode]);

  return (
    <div
      ref={chartRef}
      style={{ width: '100%', height: '100%' }}
      aria-label="知识图谱"
    />
  );
};

export default KnowledgeGraph;
