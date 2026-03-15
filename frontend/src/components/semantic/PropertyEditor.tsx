import React, { useState } from 'react';
import { Card, Table, Button, Select, Input, Typography, Divider } from 'antd';
import { PlusOutlined, EditOutlined } from '@ant-design/icons';
import { SemanticObject } from '../../types/semantic';
import FormulaBuilder from './FormulaBuilder';

const { Text } = Typography;

interface PropertyEditorProps {
  objectName: string;
  objectMeta: SemanticObject | null;
  projectId: number;
  onTestFormula: (formula: string) => Promise<{ sql: string | null; error: string | null }>;
  onChange: (updated: SemanticObject) => void;
}

const SEMANTIC_TYPES = [
  { value: '', label: '默认' },
  { value: 'currency', label: '货币' },
  { value: 'percentage', label: '百分比' },
  { value: 'enum', label: '枚举' },
  { value: 'date', label: '日期' },
  { value: 'id', label: 'ID' },
  { value: 'text', label: '文本' },
];

const PropertyEditor: React.FC<PropertyEditorProps> = ({
  objectName, objectMeta, projectId: _projectId, onTestFormula, onChange
}) => {
  const [formulaBuilderOpen, setFormulaBuilderOpen] = useState(false);
  const [editingComputed, setEditingComputed] = useState<string | null>(null);

  if (!objectMeta) {
    return <Card><Text type="secondary">请从左侧选择一个对象</Text></Card>;
  }

  const updateBaseProperty = (propName: string, field: string, value: any) => {
    const updated = {
      ...objectMeta,
      base_properties: {
        ...objectMeta.base_properties,
        [propName]: { ...objectMeta.base_properties[propName], [field]: value },
      },
    };
    onChange(updated);
  };

  const baseColumns = [
    { title: '字段名', dataIndex: 'name', key: 'name', render: (v: string) => <Text code>{v}</Text> },
    { title: '列名', dataIndex: 'column', key: 'column', render: (v: string) => <Text type="secondary">{v}</Text> },
    {
      title: '语义类型', dataIndex: 'semantic_type', key: 'semantic_type',
      render: (v: string, record: any) => (
        <Select
          size="small"
          value={v || ''}
          style={{ width: 100 }}
          options={SEMANTIC_TYPES}
          onChange={val => updateBaseProperty(record.name, 'semantic_type', val || undefined)}
        />
      )
    },
    {
      title: '描述', dataIndex: 'description', key: 'description',
      render: (v: string, record: any) => (
        <Input
          size="small"
          value={v || ''}
          placeholder="业务描述"
          onChange={e => updateBaseProperty(record.name, 'description', e.target.value)}
        />
      )
    },
  ];

  const baseData = Object.entries(objectMeta.base_properties).map(([name, prop]) => ({
    key: name, ...prop, name,
  }));

  const computedData = Object.entries(objectMeta.computed_properties).map(([name, prop]) => ({
    key: name, ...prop, name,
  }));

  const computedColumns = [
    { title: '字段名', dataIndex: 'name', key: 'name', render: (v: string) => <Text code>{v}</Text> },
    { title: '公式', dataIndex: 'formula', key: 'formula', render: (v: string) => <Text type="secondary" style={{ fontFamily: 'monospace' }}>{v}</Text> },
    { title: '描述', dataIndex: 'description', key: 'description' },
    {
      title: '操作', key: 'action',
      render: (_: any, record: any) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => { setEditingComputed(record.name); setFormulaBuilderOpen(true); }}>
          编辑
        </Button>
      )
    },
  ];

  const handleFormulaSave = (formula: string) => {
    if (!editingComputed) return;
    const updated = {
      ...objectMeta,
      computed_properties: {
        ...objectMeta.computed_properties,
        [editingComputed]: { ...objectMeta.computed_properties[editingComputed], formula },
      },
    };
    onChange(updated);
    setFormulaBuilderOpen(false);
    setEditingComputed(null);
  };

  return (
    <div style={{ padding: 16 }}>
      <Card title={<><Text strong>{objectName}</Text> — 基础字段</>} size="small">
        <Table columns={baseColumns} dataSource={baseData} pagination={false} size="small" />
      </Card>

      <Divider />

      <Card
        title={<><Text strong>{objectName}</Text> — 计算字段</>}
        size="small"
        extra={
          <Button size="small" icon={<PlusOutlined />} onClick={() => {
            const name = `new_field_${Date.now()}`;
            const updated = {
              ...objectMeta,
              computed_properties: {
                ...objectMeta.computed_properties,
                [name]: { name, semantic_type: 'computed' as const, formula: '', description: '' },
              },
            };
            onChange(updated);
            setEditingComputed(name);
            setFormulaBuilderOpen(true);
          }}>
            添加计算字段
          </Button>
        }
      >
        <Table columns={computedColumns} dataSource={computedData} pagination={false} size="small" />
      </Card>

      <FormulaBuilder
        open={formulaBuilderOpen}
        objectName={objectName}
        objectMeta={objectMeta}
        initialFormula={editingComputed ? objectMeta.computed_properties[editingComputed]?.formula : ''}
        onSave={handleFormulaSave}
        onCancel={() => { setFormulaBuilderOpen(false); setEditingComputed(null); }}
        onTest={onTestFormula}
      />
    </div>
  );
};

export default PropertyEditor;
