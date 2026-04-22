import React, { useState, useEffect } from 'react';
import { Save, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import CodeMirror from '@uiw/react-codemirror';
import { yaml } from '@codemirror/lang-yaml';
import { useProject } from '@/contexts/ProjectContext';
import { projectService } from '@/services/project';
import { ontologyService } from '@/services/ontology';
import ProjectList from './ProjectList';
import ApiKeyManager from '../components/ApiKeyManager';
import DatasourceManager from './DatasourceManager';
import OntologyEditor from './OntologyEditor';

const NoProjectHint = () => (
  <p className="text-slate-400 text-sm text-center py-8">请先在顶部选择一个项目</p>
);

const Settings: React.FC = () => {
  const { currentProject, refreshProjects } = useProject();
  const [config, setConfig] = useState('');
  const [statusMsg, setStatusMsg] = useState('');

  useEffect(() => {
    if (currentProject) setConfig(currentProject.omaha_config || '');
  }, [currentProject]);

  const handleSave = async () => {
    if (!currentProject) return;
    await projectService.update(currentProject.id, { omaha_config: config });
    await refreshProjects();
    setStatusMsg('已保存');
    setTimeout(() => setStatusMsg(''), 2000);
  };

  const handleValidate = async () => {
    const result = await ontologyService.validate(config);
    setStatusMsg(result.valid ? '配置有效' : `错误: ${result.errors.join(', ')}`);
    setTimeout(() => setStatusMsg(''), 3000);
  };

  return (
    <div className="space-y-4">
      <h1 className="text-white text-xl font-semibold">设置</h1>

      <Tabs defaultValue="projects" className="w-full">
        <TabsList className="bg-surface border border-white/10">
          <TabsTrigger value="projects" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
            项目管理
          </TabsTrigger>
          <TabsTrigger value="config" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
            配置编辑
          </TabsTrigger>
          <TabsTrigger value="datasources" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
            数据源
          </TabsTrigger>
          <TabsTrigger value="ontology" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
            本体建模
          </TabsTrigger>
          <TabsTrigger value="apikeys" className="data-[state=active]:bg-primary/20 data-[state=active]:text-primary">
            API Keys
          </TabsTrigger>
        </TabsList>

        <TabsContent value="projects" className="mt-4">
          <ProjectList />
        </TabsContent>

        <TabsContent value="datasources" className="mt-4">
          {currentProject ? (
            <DatasourceManager projectId={currentProject.id} />
          ) : (
            <NoProjectHint />
          )}
        </TabsContent>

        <TabsContent value="ontology" className="mt-4">
          {currentProject ? (
            <OntologyEditor projectId={currentProject.id} />
          ) : (
            <NoProjectHint />
          )}
        </TabsContent>

        <TabsContent value="config" className="mt-4">
          {currentProject ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-slate-400 text-sm">
                  编辑 <span className="text-white">{currentProject.name}</span> 的本体配置
                </span>
                <div className="flex items-center gap-2">
                  {statusMsg && (
                    <span className="text-sm text-green-400 flex items-center gap-1">
                      <CheckCircle size={14} /> {statusMsg}
                    </span>
                  )}
                  <Button variant="ghost" size="sm" onClick={handleValidate} className="text-slate-400">
                    验证
                  </Button>
                  <Button size="sm" onClick={handleSave} className="bg-primary hover:bg-primary/90">
                    <Save size={14} className="mr-2" /> 保存
                  </Button>
                </div>
              </div>
              <CodeMirror
                value={config}
                height="600px"
                extensions={[yaml()]}
                onChange={setConfig}
                theme="dark"
              />
            </div>
          ) : (
            <NoProjectHint />
          )}
        </TabsContent>

        <TabsContent value="apikeys" className="mt-4">
          {currentProject ? (
            <ApiKeyManager projectId={currentProject.id} />
          ) : (
            <NoProjectHint />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Settings;
