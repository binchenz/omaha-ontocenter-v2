import React, { useState } from 'react';
import { Modal, Button, Input, Space, Tag, Alert, Typography } from 'antd';
import { SemanticObject } from '../../types/semantic';

const { Text } = Typography;

interface FormulaBuilderProps {
  open: boolean;
  objectName: string;
  objectMeta: SemanticObject | null;
  initialFormula?: string;
  onSave: (formula: string) => void;
  onCancel: () => void;
  onTest: (formula: string) => Promise<{ sql: string | null; error: string | null }>;
}

const OPERATORS = ['+', '-', '*', '/', '>', '<', '>=', '<=', '=', 'AND', 'OR', 'IF(', '(', ')'];

const FormulaBuilder: React.FC<FormulaBuilderProps> = ({
  open, objectName, objectMeta, initialFormula = '', onSave, onCancel, onTest
}) => {
  const [formula, setFormula] = useState(initialFormula);
  const [testResult, setTestResult] = useState<{ sql: string | null; error: string | null } | null>(null);
  const [testing, setTesting] = useState(false);

  const availableFields = objectMeta
    ? Object.keys(objectMeta.base_properties)
    : [];

  const appendToFormula = (token: string) => {
    setFormula(prev => prev ? `${prev} ${token}` : token);
    setTestResult(null);
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const result = await onTest(formula);
      setTestResult(result);
    } finally {
      setTesting(false);
    }
  };

  return (
    <Modal
      title={`公式构建器 — ${objectName}`}
      open={open}
      onCancel={onCancel}
      onOk={() => onSave(formula)}
      okText="保存"
      cancelText="取消"
      width={600}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <div>
          <Text strong>可用字段：</Text>
          <div style={{ marginTop: 8 }}>
            {availableFields.map(field => (
              <Tag
                key={field}
                color="blue"
                style={{ cursor: 'pointer', marginBottom: 4 }}
                onClick={() => appendToFormula(field)}
              >
                {field}
              </Tag>
            ))}
          </div>
        </div>

        <div>
          <Text strong>运算符：</Text>
          <div style={{ marginTop: 8 }}>
            {OPERATORS.map(op => (
              <Tag
                key={op}
                color="default"
                style={{ cursor: 'pointer', marginBottom: 4, fontFamily: 'monospace' }}
                onClick={() => appendToFormula(op)}
              >
                {op}
              </Tag>
            ))}
          </div>
        </div>

        <div>
          <Text strong>公式：</Text>
          <Input.TextArea
            value={formula}
            onChange={e => { setFormula(e.target.value); setTestResult(null); }}
            rows={3}
            style={{ fontFamily: 'monospace', marginTop: 8 }}
            placeholder="点击字段和运算符构建公式，或直接输入"
          />
        </div>

        <Button onClick={handleTest} loading={testing} disabled={!formula.trim()}>
          测试公式
        </Button>

        {testResult && (
          testResult.error
            ? <Alert type="error" message={testResult.error} />
            : <Alert type="success" message={`SQL: ${testResult.sql}`} />
        )}
      </Space>
    </Modal>
  );
};

export default FormulaBuilder;
