import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { semanticApi } from '@/services/semanticApi';
import ERDiagram from '../components/map/ERDiagram';
import KnowledgeGraph from '../components/map/KnowledgeGraph';
import NodeDetailDrawer from '../components/map/NodeDetailDrawer';

type ViewMode = 'er' | 'kg';

interface NodeInfo {
  name: string;
  fieldCount: number;
  color: string;
  nodeType: string;
}

interface Edge {
  source: string;
  target: string;
  label: string;
}

function inferNodeType(name: string): 'quote' | 'financial' | 'computed' | 'core' {
  const n = name.toLowerCase();
  if (/quote|daily|price|行情/.test(n)) return 'quote';
  if (/financial|indicator|财务|fina/.test(n)) return 'financial';
  if (/technical|computed|技术|calc/.test(n)) return 'computed';
  return 'core';
}

const NODE_COLORS: Record<string, string> = {
  quote: '#16a34a',
  financial: '#d97706',
  computed: '#7c3aed',
  core: '#2563EB',
};

const OntologyMap: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? parseInt(id) : 0;
  const navigate = useNavigate();

  const [view, setView] = useState<ViewMode>('er');
  const [nodes, setNodes] = useState<NodeInfo[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [projectName, setProjectName] = useState('');
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadOntology();
  }, [projectId]);

  const loadOntology = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await semanticApi.get(projectId);
      const objects = data.parsed?.objects || {};

      const builtNodes: NodeInfo[] = Object.entries(objects).map(([name, obj]: [string, any]) => {
        const nodeType = inferNodeType(name);
        return {
          name,
          fieldCount: Object.keys(obj.base_properties || {}).length,
          color: NODE_COLORS[nodeType],
          nodeType,
        };
      });

      const builtEdges: Edge[] = Object.entries(objects).flatMap(([objName, obj]: [string, any]) =>
        (obj.relationships || [])
          .filter((r: any) => r.from_object === objName)
          .map((r: any) => ({ source: r.from_object, target: r.to_object, label: r.name }))
      );

      setNodes(builtNodes);
      setEdges(builtEdges);
      setProjectName(`项目 ${projectId}`);
    } catch {
      setError('加载本体配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = (name: string) => {
    setSelectedNode(prev => prev === name ? null : name);
  };

  const handleViewSwitch = (newView: ViewMode) => {
    const prev = selectedNode;
    setView(newView);
    // Continuity: keep the same node selected after switch
    if (prev) setTimeout(() => setSelectedNode(prev), 50);
  };

  const selectedNodeInfo = nodes.find(n => n.name === selectedNode) || null;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <p className="text-red-400 text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden">
      {/* Top bar — 48px */}
      <div
        className="flex items-center justify-between px-4 border-b border-white/10 bg-surface shrink-0"
        style={{ height: 48 }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/projects/${projectId}`)}
            className="text-slate-400 hover:text-white flex items-center gap-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary rounded"
          >
            <ArrowLeft size={15} /> 返回项目
          </button>
          <span className="text-white/30 text-sm">|</span>
          <span className="text-white text-sm font-medium">{projectName} 本体地图</span>
        </div>

        <div className="flex items-center gap-1">
          <Button
            size="sm"
            variant={view === 'er' ? 'default' : 'ghost'}
            className={`h-7 text-xs ${view === 'er' ? 'bg-primary text-white' : 'text-slate-400'}`}
            onClick={() => handleViewSwitch('er')}
          >
            ER 图
          </Button>
          <Button
            size="sm"
            variant={view === 'kg' ? 'default' : 'ghost'}
            className={`h-7 text-xs ${view === 'kg' ? 'bg-primary text-white' : 'text-slate-400'}`}
            onClick={() => handleViewSwitch('kg')}
          >
            知识图谱
          </Button>
        </div>
      </div>

      {/* Chart area */}
      <div className="flex-1 relative" style={{ minHeight: 0 }}>
        <div style={{ width: '100%', height: '100%' }}>
          {view === 'er' ? (
            <ERDiagram
              nodes={nodes}
              edges={edges}
              selectedNode={selectedNode}
              onNodeClick={handleNodeClick}
            />
          ) : (
            <KnowledgeGraph
              nodes={nodes}
              edges={edges}
              selectedNode={selectedNode}
              onNodeClick={handleNodeClick}
              projectId={projectId}
            />
          )}
        </div>

        {/* Drawer backdrop dimming when open */}
        {selectedNode && (
          <div
            className="absolute inset-0 pointer-events-none"
            style={{ background: 'rgba(0,0,0,0.2)' }}
          />
        )}
      </div>

      {/* Detail drawer */}
      <NodeDetailDrawer
        projectId={projectId}
        objectName={selectedNode}
        fieldCount={selectedNodeInfo?.fieldCount ?? 0}
        onClose={() => setSelectedNode(null)}
      />
    </div>
  );
};

export default OntologyMap;
