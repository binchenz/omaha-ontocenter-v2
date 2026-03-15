import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Tabs, Button, message, Space } from 'antd';
import { SaveOutlined, MessageOutlined, DatabaseOutlined, AppstoreOutlined } from '@ant-design/icons';
import { projectService } from '@/services/project';
import { ontologyService } from '@/services/ontology';
import { Project } from '@/types';
import CodeMirror from '@uiw/react-codemirror';
import { yaml } from '@codemirror/lang-yaml';
import ObjectExplorer from './ObjectExplorer';
import AssetList from './AssetList';
import { ChatAgent } from './ChatAgent';

const { TabPane } = Tabs;

const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id ? parseInt(id) : undefined;
  const [project, setProject] = useState<Project | null>(null);
  const [config, setConfig] = useState('');
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);

  useEffect(() => {
    loadProject();
  }, [id]);

  const loadProject = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const data = await projectService.get(projectId);
      setProject(data);
      setConfig(data.omaha_config || '');
    } catch (error: any) {
      message.error('Failed to load project');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      await projectService.update(projectId, { omaha_config: config });
      message.success('Configuration saved successfully');
      loadProject();
    } catch (error: any) {
      message.error('Failed to save configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const result = await ontologyService.validate(config);
      if (result.valid) {
        message.success('Configuration is valid!');
        if (result.warnings.length > 0) {
          message.warning(`Warnings: ${result.warnings.join(', ')}`);
        }
      } else {
        message.error(`Validation failed: ${result.errors.join(', ')}`);
      }
    } catch (error: any) {
      message.error('Validation failed');
    } finally {
      setValidating(false);
    }
  };

  const handleBuildOntology = async () => {
    setValidating(true);
    try {
      const result = await ontologyService.build(config);
      if (result.valid) {
        message.success('Ontology built successfully!');
        console.log('Ontology:', result.ontology);
      } else {
        message.error(`Build failed: ${result.errors?.join(', ')}`);
      }
    } catch (error: any) {
      message.error('Failed to build ontology');
    } finally {
      setValidating(false);
    }
  };

  if (loading && !project) {
    return <Card loading={loading} />;
  }

  return (
    <Card
      title={`Project: ${project?.name}`}
      extra={
        <Space>
          <Button onClick={handleValidate} loading={validating}>
            Validate
          </Button>
          <Button onClick={handleBuildOntology} loading={validating}>
            Build Ontology
          </Button>
          <Button onClick={() => navigate(`/projects/${id}/semantic`)}>
            语义层
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={loading}
          >
            Save
          </Button>
        </Space>
      }
    >
      <Tabs defaultActiveKey="config">
        <TabPane tab="Configuration" key="config">
          <CodeMirror
            value={config}
            height="600px"
            extensions={[yaml()]}
            onChange={(value) => setConfig(value)}
          />
        </TabPane>
        <TabPane tab={<span><AppstoreOutlined /> Explorer</span>} key="explorer">
          <ObjectExplorer projectId={projectId} />
        </TabPane>
        <TabPane tab={<span><DatabaseOutlined /> 资产</span>} key="assets">
          <AssetList />
        </TabPane>
        <TabPane tab={<span><MessageOutlined /> Chat</span>} key="chat">
          {projectId && <ChatAgent projectIdProp={projectId} />}
        </TabPane>
      </Tabs>
    </Card>
  );
};

export default ProjectDetail;
