import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Save, CheckCircle, Key } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import CodeMirror from '@uiw/react-codemirror';
import { yaml } from '@codemirror/lang-yaml';
import { projectService } from '@/services/project';
import { ontologyService } from '@/services/ontology';
import { Project } from '@/types';
import ObjectExplorer from './ObjectExplorer';
import OntologyViewer from './OntologyViewer';
import AssetList from './AssetList';
import ApiKeyManager from '../components/ApiKeyManager';
import ChatWithSessions from './ChatWithSessions';
import QueryBuilder from './QueryBuilder';
import AggregateQuery from './AggregateQuery';
import QueryHistory from './QueryHistory';

const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? parseInt(id) : undefined;
  const [project, setProject] = useState<Project | null>(null);
  const [config, setConfig] = useState('');
  const [loading, setLoading] = useState(false);
  const [apiKeyOpen, setApiKeyOpen] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');
  const navigate = useNavigate();

  useEffect(() => { loadProject(); }, [id]);

  const loadProject = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await projectService.get(projectId);
      setProject(data);
      setConfig(data.omaha_config || '');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!projectId) return;
    await projectService.update(projectId, { omaha_config: config });
    setStatusMsg('Saved');
    setTimeout(() => setStatusMsg(''), 2000);
  };

  const handleValidate = async () => {
    const result = await ontologyService.validate(config);
    setStatusMsg(result.valid ? 'Valid' : `Error: ${result.errors.join(', ')}`);
    setTimeout(() => setStatusMsg(''), 3000);
  };

  if (loading && !project) {
    return <div className="text-slate-400 p-6">Loading...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-white text-xl font-semibold">{project?.name}</h1>
        <div className="flex items-center gap-2">
          {statusMsg && (
            <span className="text-sm text-green-400 flex items-center gap-1">
              <CheckCircle size={14} /> {statusMsg}
            </span>
          )}
          <Button variant="ghost" size="sm" onClick={() => setApiKeyOpen(true)} className="text-slate-400">
            <Key size={14} className="mr-2" /> API Keys
          </Button>
          <Button variant="ghost" size="sm" onClick={handleValidate} className="text-slate-400">
            Validate
          </Button>
          <Button size="sm" onClick={handleSave} className="bg-primary hover:bg-primary/90">
            <Save size={14} className="mr-2" /> Save
          </Button>
        </div>
      </div>

      <Tabs defaultValue="config" className="w-full">
        <TabsList className="bg-surface border border-white/10">
          <TabsTrigger value="config" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Config</TabsTrigger>
          <TabsTrigger value="ontology" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Ontology</TabsTrigger>
          <TabsTrigger value="explorer" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Explorer</TabsTrigger>
          <TabsTrigger value="assets" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Assets</TabsTrigger>
          <TabsTrigger value="chat" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">Chat</TabsTrigger>
        </TabsList>

        <TabsContent value="config" className="mt-4">
          <CodeMirror
            value={config}
            height="600px"
            extensions={[yaml()]}
            onChange={setConfig}
            theme="dark"
          />
        </TabsContent>

        <TabsContent value="ontology" className="mt-4">
          <div className="flex justify-end mb-3">
            <Button
              size="sm"
              variant="ghost"
              className="text-primary text-xs"
              onClick={() => navigate(`/projects/${projectId}/map`)}
            >
              查看本体地图
            </Button>
          </div>
          <OntologyViewer configYaml={config} />
        </TabsContent>

        <TabsContent value="explorer" className="mt-4">
          <Tabs defaultValue="objects">
            <TabsList className="bg-background border border-white/10 mb-4">
              <TabsTrigger value="objects" className="data-[state=active]:text-primary text-sm">Objects</TabsTrigger>
              <TabsTrigger value="query" className="data-[state=active]:text-primary text-sm">Query</TabsTrigger>
              <TabsTrigger value="aggregate" className="data-[state=active]:text-primary text-sm">Aggregate</TabsTrigger>
              <TabsTrigger value="history" className="data-[state=active]:text-primary text-sm">History</TabsTrigger>
            </TabsList>
            <TabsContent value="objects"><ObjectExplorer projectId={projectId} /></TabsContent>
            <TabsContent value="query">{projectId && <QueryBuilder projectId={projectId} />}</TabsContent>
            <TabsContent value="aggregate"><AggregateQuery /></TabsContent>
            <TabsContent value="history">{projectId && <QueryHistory projectId={projectId} />}</TabsContent>
          </Tabs>
        </TabsContent>

        <TabsContent value="assets" className="mt-4">
          <AssetList />
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          {projectId && <ChatWithSessions projectId={projectId} />}
        </TabsContent>
      </Tabs>

      <Dialog open={apiKeyOpen} onOpenChange={setApiKeyOpen}>
        <DialogContent className="bg-surface border-white/10 text-white max-w-2xl">
          <DialogHeader><DialogTitle>API Keys</DialogTitle></DialogHeader>
          {projectId && <ApiKeyManager projectId={projectId} />}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ProjectDetail;
