import React from 'react';
import { Card, Typography, Tag } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import { SemanticObject } from '../../types/semantic';

const { Text, Paragraph } = Typography;

interface AgentPreviewProps {
  objectName: string;
  objectMeta: SemanticObject | null;
}

const AgentPreview: React.FC<AgentPreviewProps> = ({ objectName, objectMeta }) => {
  if (!objectMeta) {
    return <Card title="Agent 上下文预览"><Text type="secondary">请选择一个对象</Text></Card>;
  }

  // 级别映射
  const levelMap: Record<string, string> = {
    master_data: '主数据',
    city_level: '城市级',
    store_level: '门店级',
    transaction: '交易级',
  };

  return (
    <Card title="Agent 上下文预览" size="small">
      <Paragraph>
        <Text strong>{objectName}</Text>
        {objectMeta.description && <Text type="secondary">（{objectMeta.description}）</Text>}
      </Paragraph>

      {/* 数据粒度区块 */}
      {objectMeta.granularity && (
        <div style={{
          background: '#f5f5f5',
          padding: '12px',
          borderRadius: '4px',
          marginBottom: '12px'
        }}>
          <Paragraph style={{ marginBottom: 8 }}>
            <BarChartOutlined style={{ marginRight: 6 }} />
            <Text strong>数据粒度:</Text>
          </Paragraph>

          {objectMeta.granularity.dimensions && objectMeta.granularity.dimensions.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary">维度: </Text>
              {objectMeta.granularity.dimensions.map((dim, idx) => (
                <Tag key={idx} color="blue" style={{ marginBottom: 4 }}>
                  {dim}
                </Tag>
              ))}
            </div>
          )}

          {objectMeta.granularity.level && (
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary">级别: </Text>
              <Tag color="green">
                {levelMap[objectMeta.granularity.level] || objectMeta.granularity.level}
              </Tag>
            </div>
          )}

          {objectMeta.granularity.description && (
            <div>
              <Text type="secondary">说明: </Text>
              <Text>{objectMeta.granularity.description}</Text>
            </div>
          )}
        </div>
      )}

      <Paragraph>
        <Text strong>字段：</Text>
      </Paragraph>

      {Object.entries(objectMeta.base_properties).map(([name, prop]) => (
        <div key={name} style={{ marginLeft: 12, marginBottom: 4 }}>
          <Text code>{name}</Text>
          {prop.semantic_type === 'currency' && <Tag color="gold" style={{ marginLeft: 4 }}>货币 {prop.currency}</Tag>}
          {prop.semantic_type === 'percentage' && <Tag color="blue" style={{ marginLeft: 4 }}>百分比</Tag>}
          {prop.semantic_type === 'enum' && <Tag color="purple" style={{ marginLeft: 4 }}>枚举</Tag>}
          {prop.description && <Text type="secondary" style={{ marginLeft: 4 }}>: {prop.description}</Text>}
        </div>
      ))}

      {Object.entries(objectMeta.computed_properties).map(([name, prop]) => (
        <div key={name} style={{ marginLeft: 12, marginBottom: 4 }}>
          <Text code>{name}</Text>
          <Tag color="green" style={{ marginLeft: 4 }}>计算</Tag>
          {prop.description && <Text type="secondary" style={{ marginLeft: 4 }}>: {prop.description}</Text>}
          <div style={{ marginLeft: 12 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>公式: {prop.formula}</Text>
          </div>
          {prop.business_context && (
            <div style={{ marginLeft: 12 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>基准: {prop.business_context}</Text>
            </div>
          )}
        </div>
      ))}

      {objectMeta.relationships.length > 0 && (
        <>
          <Paragraph style={{ marginTop: 8 }}>
            <Text strong>关系：</Text>
          </Paragraph>
          {objectMeta.relationships
            .filter(r => r.from_object === objectName || r.to_object === objectName)
            .map((rel, i) => (
              <div key={i} style={{ marginLeft: 12, marginBottom: 4 }}>
                <Text code>{rel.name}</Text>
                {rel.description && <Text type="secondary" style={{ marginLeft: 4 }}>: {rel.description}</Text>}
              </div>
            ))}
        </>
      )}
    </Card>
  );
};

export default AgentPreview;
