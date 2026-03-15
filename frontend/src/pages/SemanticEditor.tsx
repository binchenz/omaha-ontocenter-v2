import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Layout, Button, message, Spin, Typography } from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import { semanticApi } from '../services/semanticApi';
import { SemanticConfig, SemanticObject } from '../types/semantic';
import ObjectList from '../components/semantic/ObjectList';
import PropertyEditor from '../components/semantic/PropertyEditor';
import AgentPreview from '../components/semantic/AgentPreview';

const { Sider, Content, Header } = Layout;
const { Title } = Typography;

const SemanticEditor: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const projectId = id ? parseInt(id) : 0;

  const [semanticConfig, setSemanticConfig] = useState<SemanticConfig | null>(null);
  const [selectedObject, setSelectedObject] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [localObjects, setLocalObjects] = useState<Record<string, SemanticObject>>({});

  useEffect(() => {
    loadConfig();
  }, [projectId]);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await semanticApi.get(projectId);
      setSemanticConfig(data);
      setLocalObjects(data.parsed.objects || {});
      const names = Object.keys(data.parsed.objects || {});
      if (names.length > 0) setSelectedObject(names[0]);
    } catch {
      message.error('加载语义配置失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!semanticConfig) return;
    setSaving(true);
    try {
      await semanticApi.save(projectId, semanticConfig.config);
      message.success('语义配置已保存');
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleTestFormula = async (formula: string) => {
    if (!selectedObject) return { sql: null, error: '未选择对象', sample: [] };
    try {
      return await semanticApi.testFormula(projectId, selectedObject, formula);
    } catch {
      return { sql: null, error: '测试失败', sample: [] };
    }
  };

  const handleObjectChange = (updated: SemanticObject) => {
    if (!selectedObject) return;
    setLocalObjects(prev => ({ ...prev, [selectedObject]: updated }));
  };

  if (loading) return <Spin style={{ margin: '40px auto', display: 'block' }} />;

  const objectNames = Object.keys(localObjects);

  return (
    <Layout style={{ height: '100vh' }}>
      <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Title level={4} style={{ margin: 0 }}>语义层编辑器</Title>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
          保存
        </Button>
      </Header>

      <Layout>
        <Sider width={220} theme="light" style={{ borderRight: '1px solid #f0f0f0', overflow: 'auto' }}>
          <ObjectList
            objects={objectNames}
            selected={selectedObject}
            onSelect={setSelectedObject}
          />
        </Sider>

        <Content style={{ overflow: 'auto' }}>
          <PropertyEditor
            objectName={selectedObject || ''}
            objectMeta={selectedObject ? localObjects[selectedObject] : null}
            projectId={projectId}
            onTestFormula={handleTestFormula}
            onChange={handleObjectChange}
          />
        </Content>

        <Sider width={300} theme="light" style={{ borderLeft: '1px solid #f0f0f0', overflow: 'auto', padding: 8 }}>
          <AgentPreview
            objectName={selectedObject || ''}
            objectMeta={selectedObject ? localObjects[selectedObject] : null}
          />
        </Sider>
      </Layout>
    </Layout>
  );
};

export default SemanticEditor;
