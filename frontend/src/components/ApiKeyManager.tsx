import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Input, Tag, Space, message, Alert, Typography, Tooltip } from 'antd';
import { PlusOutlined, DeleteOutlined, CopyOutlined, KeyOutlined } from '@ant-design/icons';
import { apiKeyService, ApiKey, ApiKeyCreated } from '../services/apiKeyService';

const { Text } = Typography;

interface ApiKeyManagerProps {
  projectId: number;
}

const ApiKeyManager: React.FC<ApiKeyManagerProps> = ({ projectId }) => {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [createdKey, setCreatedKey] = useState<ApiKeyCreated | null>(null);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadKeys();
  }, [projectId]);

  const loadKeys = async () => {
    setLoading(true);
    try {
      const data = await apiKeyService.list(projectId);
      setKeys(data);
    } catch {
      message.error('加载 API Key 失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const created = await apiKeyService.create(projectId, newKeyName.trim());
      setCreatedKey(created);
      setNewKeyName('');
      loadKeys();
    } catch {
      message.error('创建 API Key 失败');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId: number) => {
    try {
      await apiKeyService.revoke(projectId, keyId);
      message.success('API Key 已撤销');
      loadKeys();
    } catch {
      message.error('撤销失败');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success('已复制到剪贴板');
  };

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '前缀', dataIndex: 'key_prefix', key: 'key_prefix',
      render: (v: string) => <Text code>omaha_*_{v}...</Text>
    },
    {
      title: '状态', dataIndex: 'is_active', key: 'is_active',
      render: (v: boolean) => v ? <Tag color="green">有效</Tag> : <Tag color="red">已撤销</Tag>
    },
    {
      title: '创建时间', dataIndex: 'created_at', key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString('zh-CN')
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, record: ApiKey) => (
        record.is_active ? (
          <Button
            danger size="small" icon={<DeleteOutlined />}
            onClick={() => handleRevoke(record.id)}
          >
            撤销
          </Button>
        ) : null
      )
    },
  ];

  return (
    <div style={{ padding: 16 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button
          type="primary" icon={<PlusOutlined />}
          onClick={() => setCreateModalOpen(true)}
        >
          生成 API Key
        </Button>
      </Space>

      <Alert
        type="info"
        style={{ marginBottom: 16 }}
        message="API Key 用于连接外部 Agent（如 Claude Desktop）"
        description={
          <div>
            <div>配置 Claude Desktop：在 <Text code>claude_desktop_config.json</Text> 中添加：</div>
            <pre style={{ fontSize: 12, marginTop: 8, background: '#f5f5f5', padding: 8 }}>{`{
  "mcpServers": {
    "omaha": {
      "command": "/opt/homebrew/bin/python3.11",
      "args": ["-m", "app.mcp.server"],
      "env": { "OMAHA_API_KEY": "your_key_here" }
    }
  }
}`}</pre>
          </div>
        }
        showIcon
      />

      <Table
        columns={columns}
        dataSource={keys.map(k => ({ ...k, key: k.id }))}
        loading={loading}
        pagination={false}
        size="small"
      />

      <Modal
        title={<><KeyOutlined /> 生成新 API Key</>}
        open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); setCreatedKey(null); setNewKeyName(''); }}
        footer={null}
      >
        {!createdKey ? (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text>为这个 Key 起一个名字（如 "claude-desktop"）：</Text>
            <Input
              value={newKeyName}
              onChange={e => setNewKeyName(e.target.value)}
              placeholder="Key 名称"
              onPressEnter={handleCreate}
            />
            <Button type="primary" loading={creating} onClick={handleCreate} disabled={!newKeyName.trim()}>
              生成
            </Button>
          </Space>
        ) : (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Alert type="warning" message="请立即复制此 Key，关闭后将无法再次查看！" showIcon />
            <Text strong>你的 API Key：</Text>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <Text code style={{ flex: 1, wordBreak: 'break-all' }}>{createdKey.key}</Text>
              <Tooltip title="复制">
                <Button icon={<CopyOutlined />} onClick={() => copyToClipboard(createdKey.key)} />
              </Tooltip>
            </div>
            <Button onClick={() => { setCreateModalOpen(false); setCreatedKey(null); }}>
              我已保存，关闭
            </Button>
          </Space>
        )}
      </Modal>
    </div>
  );
};

export default ApiKeyManager;
