import React, { useEffect, useRef } from 'react';
import * as echarts from 'echarts';


interface LineageNode {
  urn: string;
  type: string;
  name: string;
}

interface AssetLineage {
  upstream: LineageNode[];
  downstream: LineageNode[];
}

interface LineageGraphProps {
  assetName: string;
  lineage: AssetLineage;
}

const LineageGraph: React.FC<LineageGraphProps> = ({ assetName, lineage }) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<echarts.ECharts | null>(null);

  const hasData = lineage.upstream.length > 0 || lineage.downstream.length > 0;

  useEffect(() => {
    if (!chartRef.current || !hasData) return;

    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current);
    }

    const nodes: any[] = [
      {
        id: 'asset',
        name: assetName,
        symbolSize: 60,
        itemStyle: { color: '#1890ff' },
        label: { show: true, fontSize: 12 },
        category: 0,
      },
    ];

    const edges: any[] = [];

    lineage.upstream.forEach((node, index) => {
      const nodeId = `upstream_${index}`;
      nodes.push({
        id: nodeId,
        name: node.name || node.urn || `Upstream ${index + 1}`,
        symbolSize: 40,
        itemStyle: { color: '#52c41a' },
        label: { show: true, fontSize: 11 },
        category: 1,
      });
      edges.push({
        source: nodeId,
        target: 'asset',
        lineStyle: { color: '#aaa', width: 2 },
        label: { show: true, formatter: node.type || 'upstream', fontSize: 10 },
      });
    });

    lineage.downstream.forEach((node, index) => {
      const nodeId = `downstream_${index}`;
      nodes.push({
        id: nodeId,
        name: node.name || node.urn || `Downstream ${index + 1}`,
        symbolSize: 40,
        itemStyle: { color: '#faad14' },
        label: { show: true, fontSize: 11 },
        category: 2,
      });
      edges.push({
        source: 'asset',
        target: nodeId,
        lineStyle: { color: '#aaa', width: 2 },
        label: { show: true, formatter: node.type || 'downstream', fontSize: 10 },
      });
    });

    const option = {
      tooltip: {
        trigger: 'item',
        formatter: (params: any) => {
          if (params.dataType === 'node') return params.data.name;
          return params.data.label?.formatter || '';
        },
      },
      legend: [
        {
          data: ['资产', '上游', '下游'],
          orient: 'vertical',
          left: 10,
          top: 10,
        },
      ],
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: edges,
          categories: [
            { name: '资产', itemStyle: { color: '#1890ff' } },
            { name: '上游', itemStyle: { color: '#52c41a' } },
            { name: '下游', itemStyle: { color: '#faad14' } },
          ],
          roam: true,
          label: { position: 'bottom' },
          force: { repulsion: 200, edgeLength: 120 },
          emphasis: { focus: 'adjacency', lineStyle: { width: 4 } },
        },
      ],
    };

    chartInstanceRef.current.setOption(option);

    const handleResize = () => chartInstanceRef.current?.resize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [assetName, lineage, hasData]);

  useEffect(() => {
    return () => {
      chartInstanceRef.current?.dispose();
      chartInstanceRef.current = null;
    };
  }, []);

  if (!hasData) {
    return <p className="text-slate-400 text-sm text-center py-8">暂无血缘数据</p>;
  }

  return <div ref={chartRef} style={{ width: '100%', height: '400px' }} />;
};

export default LineageGraph;
