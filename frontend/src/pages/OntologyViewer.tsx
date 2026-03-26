import React, { useState, useMemo } from 'react';
import { parse } from 'yaml';
import {
  Row, Col, Card, List, Tag, Table, Typography, Input,
  Badge, Tooltip, Empty, Alert,
} from 'antd';
import {
  DatabaseOutlined, LinkOutlined, FilterOutlined,
  FunctionOutlined, NodeIndexOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;
const { Search } = Input;

interface OntologyViewerProps {
  configYaml: string;
}

const TYPE_COLORS: Record<string, string> = {
  string: 'blue',
  integer: 'green',
  float: 'cyan',
  decimal: 'cyan',
  currency: 'gold',
  date: 'orange',
  boolean: 'purple',
  computed: 'magenta',
};

const OntologyViewer: React.FC<OntologyViewerProps> = ({ configYaml }) => {
  const [selectedObject, setSelectedObject] = useState<string | null>(null);
  const [selectedRelationship, setSelectedRelationship] = useState<string | null>(null);
  const [propSearch, setPropSearch] = useState('');

  const parsed = useMemo(() => {
    if (!configYaml?.trim()) return null;
    try {
      return parse(configYaml);
    } catch {
      return null;
    }
  }, [configYaml]);

  if (!parsed) {
    return <Empty description="暂无有效的 Ontology 配置，请先在 Configuration 中填写 YAML" />;
  }

  const objects: any[] = parsed?.ontology?.objects ?? [];
  const relationships: any[] = parsed?.ontology?.relationships ?? [];

  const currentObj = objects.find((o) => o.name === selectedObject);
  const currentRel = relationships.find((r) => r.name === selectedRelationship);

  const relatedRels = currentObj
    ? relationships.filter(
        (r) => r.from_object === currentObj.name || r.to_object === currentObj.name
      )
    : [];

  const filteredProps = (currentObj?.properties ?? []).filter(
    (p: any) =>
      !propSearch ||
      p.name?.toLowerCase().includes(propSearch.toLowerCase()) ||
      p.description?.toLowerCase().includes(propSearch.toLowerCase())
  );

  const propColumns = [
    {
      title: '属性名',
      dataIndex: 'name',
      key: 'name',
      width: 180,
      render: (v: string) => <Text code>{v}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (v: string) => (
        <Tag color={TYPE_COLORS[v] ?? 'default'}>{v}</Tag>
      ),
    },
    {
      title: '列名',
      dataIndex: 'column',
      key: 'column',
      width: 180,
      render: (v: string, row: any) => (
        <Text type="secondary">{v || row.column_name || '-'}</Text>
      ),
    },
    {
      title: '描述 / 业务含义',
      dataIndex: 'description',
      key: 'description',
      render: (v: string, row: any) => (
        <span>
          {v || '-'}
          {row.business_context && (
            <Tooltip title={row.business_context}>
              <Text type="secondary" style={{ marginLeft: 6, cursor: 'help' }}>[?]</Text>
            </Tooltip>
          )}
        </span>
      ),
    },
  ];

  return (
    <Row gutter={16} style={{ minHeight: 600 }}>
      {/* Left: Object & Relationship list */}
      <Col span={6}>
        <Card
          size="small"
          title={<span><DatabaseOutlined /> Objects ({objects.length})</span>}
          style={{ marginBottom: 12 }}
          bodyStyle={{ padding: 0 }}
        >
          <List
            size="small"
            dataSource={objects}
            renderItem={(obj: any) => (
              <List.Item
                onClick={() => { setSelectedObject(obj.name); setSelectedRelationship(null); }}
                style={{
                  cursor: 'pointer',
                  padding: '8px 12px',
                  background: selectedObject === obj.name ? '#e6f4ff' : undefined,
                  borderLeft: selectedObject === obj.name ? '3px solid #1677ff' : '3px solid transparent',
                }}
              >
                <span style={{ fontWeight: selectedObject === obj.name ? 600 : 400 }}>
                  {obj.name}
                </span>
                <Badge
                  count={(obj.properties ?? []).length}
                  style={{ backgroundColor: '#52c41a', marginLeft: 8 }}
                />
              </List.Item>
            )}
          />
        </Card>

        {relationships.length > 0 && <Card
          size="small"
          title={<span><LinkOutlined /> Relationships ({relationships.length})</span>}
          bodyStyle={{ padding: 0 }}
        >
          <List
            size="small"
            dataSource={relationships}
            renderItem={(rel: any) => (
              <List.Item
                onClick={() => { setSelectedRelationship(rel.name); setSelectedObject(null); }}
                style={{
                  cursor: 'pointer',
                  padding: '8px 12px',
                  background: selectedRelationship === rel.name ? '#e6f4ff' : undefined,
                  borderLeft: selectedRelationship === rel.name ? '3px solid #1677ff' : '3px solid transparent',
                }}
              >
                <div style={{ fontSize: 12 }}>
                  <div style={{ fontWeight: selectedRelationship === rel.name ? 600 : 400 }}>
                    {rel.name}
                  </div>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {rel.from_object} → {rel.to_object}
                  </Text>
                </div>
              </List.Item>
            )}
          />
        </Card>}
      </Col>

      {/* Right: Detail panel */}
      <Col span={18}>
        {!currentObj && !currentRel && (
          <Empty
            style={{ marginTop: 80 }}
            description="从左侧选择一个 Object 或 Relationship 查看详情"
          />
        )}

        {/* Object detail */}
        {currentObj && (
          <>
            {/* Header card */}
            <Card
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <span style={{ fontSize: 16 }}>
                  <DatabaseOutlined style={{ marginRight: 8 }} />
                  {currentObj.name}
                </span>
              }
            >
              <Row gutter={16}>
                <Col span={12}>
                  <Text type="secondary">表名：</Text>
                  <Text code>{currentObj.table}</Text>
                </Col>
                <Col span={12}>
                  <Text type="secondary">数据源：</Text>
                  <Tag>{currentObj.datasource || '-'}</Tag>
                </Col>
              </Row>
              {currentObj.description && (
                <Paragraph style={{ marginTop: 8, marginBottom: 0 }} type="secondary">
                  {currentObj.description}
                </Paragraph>
              )}
              {currentObj.business_context && (
                <Alert
                  style={{ marginTop: 8 }}
                  type="info"
                  message="业务背景"
                  description={<pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 12 }}>{currentObj.business_context}</pre>}
                  showIcon
                />
              )}
            </Card>

            {/* default_filters */}
            {currentObj.default_filters?.length > 0 && (
              <Card
                size="small"
                style={{ marginBottom: 12 }}
                title={<span><FilterOutlined /> 默认过滤条件（自动应用）</span>}
              >
                {currentObj.default_filters.map((f: any, i: number) => (
                  <Tag key={i} color="volcano" style={{ marginBottom: 4 }}>
                    {f.field} {f.operator} {f.value !== undefined ? `'${f.value}'` : ''}
                  </Tag>
                ))}
              </Card>
            )}

            {/* computed_properties */}
            {currentObj.computed_properties?.length > 0 && (
              <Card
                size="small"
                style={{ marginBottom: 12 }}
                title={<span><FunctionOutlined /> 计算属性 ({currentObj.computed_properties.length})</span>}
              >
                <List
                  size="small"
                  dataSource={currentObj.computed_properties}
                  renderItem={(cp: any) => (
                    <List.Item style={{ alignItems: 'flex-start' }}>
                      <div>
                        <Text code>{cp.name}</Text>
                        <Tag color="magenta" style={{ marginLeft: 8 }}>{cp.type}</Tag>
                        {cp.description && <Text type="secondary" style={{ marginLeft: 8 }}>{cp.description}</Text>}
                        <div style={{ marginTop: 4 }}>
                          <Text type="secondary" style={{ fontSize: 11 }}>formula: </Text>
                          <Text code style={{ fontSize: 11 }}>{cp.formula}</Text>
                        </div>
                      </div>
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {/* Properties table */}
            <Card
              size="small"
              style={{ marginBottom: 12 }}
              title={
                <Row justify="space-between" align="middle">
                  <Col>Properties ({(currentObj.properties ?? []).length})</Col>
                  <Col>
                    <Search
                      placeholder="搜索属性"
                      allowClear
                      size="small"
                      style={{ width: 200 }}
                      onChange={(e) => setPropSearch(e.target.value)}
                    />
                  </Col>
                </Row>
              }
            >
              <Table
                size="small"
                dataSource={filteredProps}
                columns={propColumns}
                rowKey="name"
                pagination={{ pageSize: 15, size: 'small' }}
                scroll={{ y: 320 }}
              />
            </Card>

            {/* Related relationships */}
            {relatedRels.length > 0 && (
              <Card
                size="small"
                title={<span><NodeIndexOutlined /> 参与的关联关系 ({relatedRels.length})</span>}
              >
                <List
                  size="small"
                  dataSource={relatedRels}
                  renderItem={(rel: any) => (
                    <List.Item>
                      <div>
                        <Tag color={rel.from_object === currentObj.name ? 'blue' : 'green'}>
                          {rel.from_object === currentObj.name ? 'FROM' : 'TO'}
                        </Tag>
                        <Text strong>{rel.name}</Text>
                        <Text type="secondary" style={{ marginLeft: 8 }}>
                          {rel.from_object} → {rel.to_object}
                        </Text>
                        <Tag style={{ marginLeft: 8 }}>{rel.join_type || 'LEFT'} JOIN</Tag>
                        {rel.join_condition && (
                          <Text code style={{ fontSize: 11, marginLeft: 8 }}>
                            ON {rel.join_condition.from_field} = {rel.join_condition.to_field}
                          </Text>
                        )}
                      </div>
                    </List.Item>
                  )}
                />
              </Card>
            )}
          </>
        )}

        {/* Relationship detail */}
        {currentRel && (
          <Card
            size="small"
            title={<span><LinkOutlined style={{ marginRight: 8 }} />{currentRel.name}</span>}
          >
            <Row gutter={16} style={{ marginBottom: 12 }}>
              <Col span={8}>
                <Text type="secondary">类型：</Text>
                <Tag color="blue">{currentRel.type || 'many_to_one'}</Tag>
              </Col>
              <Col span={8}>
                <Text type="secondary">JOIN 方式：</Text>
                <Tag>{currentRel.join_type || 'LEFT'} JOIN</Tag>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="From" style={{ textAlign: 'center' }}>
                  <Text strong style={{ fontSize: 16 }}>{currentRel.from_object}</Text>
                  {currentRel.join_condition && (
                    <div><Text code style={{ fontSize: 12 }}>{currentRel.join_condition.from_field}</Text></div>
                  )}
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="To" style={{ textAlign: 'center' }}>
                  <Text strong style={{ fontSize: 16 }}>{currentRel.to_object}</Text>
                  {currentRel.join_condition && (
                    <div><Text code style={{ fontSize: 12 }}>{currentRel.join_condition.to_field}</Text></div>
                  )}
                </Card>
              </Col>
            </Row>
            {currentRel.description && (
              <Paragraph style={{ marginTop: 12 }} type="secondary">{currentRel.description}</Paragraph>
            )}
          </Card>
        )}
      </Col>
    </Row>
  );
};

export default OntologyViewer;
