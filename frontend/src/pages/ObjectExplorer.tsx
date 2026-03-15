import React, { useState, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import {
  Card,
  Select,
  Button,
  Table,
  message,
  Space,
  Checkbox,
  Input,
  Row,
  Col,
  Divider,
  Modal,
  Form,
} from 'antd';
import { SearchOutlined, PlusOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons';
import { queryService } from '@/services/query';
import { assetService } from '@/services/asset';

const { Option } = Select;

interface ObjectExplorerProps {
  projectId?: number;
}

interface Filter {
  field: string;
  operator: string;
  value: string;
}

interface Column {
  name: string;
  type: string;
  description: string;
}

interface Relationship {
  name: string;
  description: string;
  from_object: string;
  to_object: string;
  type: string;
  join_condition: { from_field: string; to_field: string };
  direction: string;
}

interface JoinConfig {
  relationship_name: string;
  join_type: string;
  relationship: Relationship;
}

const ObjectExplorer: React.FC<ObjectExplorerProps> = ({ projectId: propProjectId }) => {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const projectId = propProjectId || (id ? parseInt(id) : undefined);

  // State
  const [objectTypes, setObjectTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [allColumns, setAllColumns] = useState<Column[]>([]);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [filters, setFilters] = useState<Filter[]>([]);
  const [availableRelationships, setAvailableRelationships] = useState<Relationship[]>([]);
  const [joins, setJoins] = useState<JoinConfig[]>([]);
  const [showJoinModal, setShowJoinModal] = useState(false);
  const [selectedRelationship, setSelectedRelationship] = useState<string>('');
  const [selectedJoinType, setSelectedJoinType] = useState<string>('LEFT');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [showSaveAssetModal, setShowSaveAssetModal] = useState(false);
  const [saveAssetForm] = Form.useForm();

  useEffect(() => {
    loadObjectTypes();
  }, [projectId]);

  useEffect(() => {
    if (selectedType) {
      loadObjectSchema();
      loadRelationships();
    }
  }, [selectedType]);

  // Load asset configuration if passed from AssetList
  useEffect(() => {
    const state = location.state as { assetConfig?: any };
    if (state?.assetConfig) {
      const config = state.assetConfig;
      setSelectedType(config.object_type);
      if (config.selected_columns) {
        setSelectedColumns(config.selected_columns);
      }
      if (config.filters) {
        setFilters(config.filters);
      }
      if (config.joins) {
        // Load joins - will need to fetch relationship details
        setJoins(
          config.joins.map((j: any) => ({
            relationship_name: j.relationship_name,
            join_type: j.join_type,
            relationship: {} as Relationship, // Will be populated when relationships load
          }))
        );
      }
    }
  }, [location.state]);

  const loadObjectTypes = async () => {
    if (!projectId) return;
    try {
      const result = await queryService.listObjectTypes(projectId);
      setObjectTypes(result.objects || []);
    } catch (error: any) {
      message.error('Failed to load object types');
    }
  };

  const loadRelationships = async () => {
    if (!projectId || !selectedType) return;
    try {
      const result = await queryService.getRelationships(projectId, selectedType);
      setAvailableRelationships(result.relationships || []);
    } catch (error: any) {
      message.error('Failed to load relationships');
    }
  };

  const loadObjectSchema = async () => {
    if (!projectId || !selectedType) return;
    try {
      const result = await queryService.getObjectSchema(projectId, selectedType);
      if (result.success && result.columns) {
        setAllColumns(result.columns);
        setSelectedColumns(result.columns.map((col) => col.name));
      }
    } catch (error: any) {
      message.error('Failed to load schema');
    }
  };

  const handleQuery = async () => {
    if (!projectId || !selectedType) return;
    if (selectedColumns.length === 0) {
      message.warning('Please select at least one column');
      return;
    }

    setLoading(true);
    try {
      const result = await queryService.queryObjects(
        projectId,
        selectedType,
        selectedColumns,
        filters.filter((f) => f.field && f.operator && f.value),
        joins.length > 0 ? joins.map(j => ({ relationship_name: j.relationship_name, join_type: j.join_type })) : undefined,
        100
      );

      if (result.success && result.data) {
        setData(result.data);
        message.success(`Found ${result.count} records`);
      } else {
        message.error(result.error || 'Query failed');
      }
    } catch (error: any) {
      message.error('Failed to query objects');
    } finally {
      setLoading(false);
    }
  };

  const addFilter = () => {
    setFilters([...filters, { field: '', operator: '=', value: '' }]);
  };

  const removeFilter = (index: number) => {
    setFilters(filters.filter((_, i) => i !== index));
  };

  const updateFilter = (index: number, key: keyof Filter, value: string) => {
    const newFilters = [...filters];
    newFilters[index][key] = value;
    setFilters(newFilters);
  };

  const addJoin = () => {
    setShowJoinModal(true);
    setSelectedRelationship('');
    setSelectedJoinType('LEFT');
  };

  const confirmJoin = () => {
    if (!selectedRelationship) {
      message.warning('Please select a relationship');
      return;
    }
    const relationship = availableRelationships.find(r => r.name === selectedRelationship);
    if (!relationship) return;

    setJoins([...joins, {
      relationship_name: selectedRelationship,
      join_type: selectedJoinType,
      relationship
    }]);
    setShowJoinModal(false);
    message.success('JOIN added successfully');
  };

  const removeJoin = (index: number) => {
    setJoins(joins.filter((_, i) => i !== index));
  };

  const handleSaveAsset = async (values: { name: string; description?: string }) => {
    if (!projectId || !selectedType) {
      message.error('No query to save');
      return;
    }

    try {
      await assetService.saveAsset(projectId, {
        name: values.name,
        description: values.description,
        query_config: {
          object_type: selectedType,
          selected_columns: selectedColumns,
          filters: filters.filter((f) => f.field && f.operator && f.value),
          joins: joins.map((j) => ({
            relationship_name: j.relationship_name,
            join_type: j.join_type,
          })),
        },
        row_count: data.length,
      });
      message.success('Asset saved successfully');
      setShowSaveAssetModal(false);
      saveAssetForm.resetFields();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to save asset');
    }
  };

  const selectAllColumns = () => {
    setSelectedColumns(allColumns.map((col: Column) => col.name));
  };

  const clearAllColumns = () => {
    setSelectedColumns([]);
  };

  if (objectTypes.length === 0) {
    return (
      <Card title="Object Explorer">
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Object Explorer will be available here after configuration is saved.</p>
        </div>
      </Card>
    );
  }

  return (
    <div>
      <Card title="Object Explorer" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* Object Selector */}
          <Row gutter={16}>
            <Col span={12}>
              <Select
                style={{ width: '100%' }}
                placeholder="Select object type"
                value={selectedType}
                onChange={setSelectedType}
              >
                {objectTypes.map((type) => (
                  <Option key={type} value={type}>
                    {type}
                  </Option>
                ))}
              </Select>
            </Col>
            <Col span={12}>
              <Space style={{ width: '100%' }}>
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={handleQuery}
                  disabled={!selectedType || selectedColumns.length === 0}
                  loading={loading}
                  style={{ flex: 1 }}
                >
                  Query
                </Button>
                <Button
                  icon={<SaveOutlined />}
                  onClick={() => setShowSaveAssetModal(true)}
                  disabled={!selectedType || data.length === 0}
                >
                  Save as Asset
                </Button>
              </Space>
            </Col>
          </Row>

          {selectedType && (
            <>
              <Divider orientation="left">Select Columns</Divider>
              <div>
                <Space style={{ marginBottom: 8 }}>
                  <Button size="small" onClick={selectAllColumns}>
                    Select All
                  </Button>
                  <Button size="small" onClick={clearAllColumns}>
                    Clear All
                  </Button>
                </Space>
                <Checkbox.Group
                  style={{ width: '100%' }}
                  value={selectedColumns}
                  onChange={(values) => setSelectedColumns(values as string[])}
                >
                  <Row>
                    {allColumns.map((col) => (
                      <Col span={8} key={col.name}>
                        <Checkbox value={col.name}>{col.name}</Checkbox>
                      </Col>
                    ))}
                  </Row>
                </Checkbox.Group>
              </div>

              <Divider orientation="left">Join Objects</Divider>
              <div>
                {joins.map((join, index) => (
                  <Space key={index} style={{ marginBottom: 8, width: '100%' }}>
                    <span style={{ width: 150 }}>
                      {join.relationship.to_object}
                    </span>
                    <span style={{ width: 100 }}>
                      {join.join_type} JOIN
                    </span>
                    <span style={{ flex: 1, color: '#888' }}>
                      {join.relationship.description}
                    </span>
                    <Button
                      icon={<DeleteOutlined />}
                      onClick={() => removeJoin(index)}
                      danger
                    />
                  </Space>
                ))}
                <Button icon={<PlusOutlined />} onClick={addJoin} disabled={availableRelationships.length === 0}>
                  Add JOIN
                </Button>
              </div>

              <Divider orientation="left">Filters</Divider>
              <div>
                {filters.map((filter, index) => (
                  <Space key={index} style={{ marginBottom: 8, width: '100%' }}>
                    <Select
                      style={{ width: 150 }}
                      placeholder="Field"
                      value={filter.field || undefined}
                      onChange={(v) => updateFilter(index, 'field', v)}
                    >
                      {allColumns.map((col) => (
                        <Option key={col.name} value={col.name}>
                          {col.name}
                        </Option>
                      ))}
                    </Select>

                    <Select
                      style={{ width: 100 }}
                      placeholder="Operator"
                      value={filter.operator}
                      onChange={(v) => updateFilter(index, 'operator', v)}
                    >
                      <Option value="=">=</Option>
                      <Option value=">">{'>'}</Option>
                      <Option value="<">{'<'}</Option>
                      <Option value=">=">{'≥'}</Option>
                      <Option value="<=">{'≤'}</Option>
                      <Option value="!=">≠</Option>
                      <Option value="LIKE">LIKE</Option>
                      <Option value="IN">IN</Option>
                    </Select>

                    <Input
                      style={{ width: 200 }}
                      placeholder="Value"
                      value={filter.value}
                      onChange={(e) => updateFilter(index, 'value', e.target.value)}
                    />

                    <Button
                      icon={<DeleteOutlined />}
                      onClick={() => removeFilter(index)}
                      danger
                    />
                  </Space>
                ))}
                <Button icon={<PlusOutlined />} onClick={addFilter}>
                  Add Filter
                </Button>
              </div>
            </>
          )}
        </Space>
      </Card>

      <Modal
        title="Add JOIN"
        open={showJoinModal}
        onOk={confirmJoin}
        onCancel={() => setShowJoinModal(false)}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <label>Relationship:</label>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              placeholder="Select relationship"
              value={selectedRelationship}
              onChange={setSelectedRelationship}
            >
              {availableRelationships.map((rel) => (
                <Option key={rel.name} value={rel.name}>
                  {rel.to_object} - {rel.description}
                </Option>
              ))}
            </Select>
          </div>
          <div>
            <label>Join Type:</label>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              value={selectedJoinType}
              onChange={setSelectedJoinType}
            >
              <Option value="LEFT">LEFT JOIN</Option>
              <Option value="INNER">INNER JOIN</Option>
              <Option value="RIGHT">RIGHT JOIN</Option>
            </Select>
          </div>
        </Space>
      </Modal>

      <Modal
        title="Save as Asset"
        open={showSaveAssetModal}
        onOk={() => saveAssetForm.submit()}
        onCancel={() => {
          setShowSaveAssetModal(false);
          saveAssetForm.resetFields();
        }}
      >
        <Form form={saveAssetForm} onFinish={handleSaveAsset} layout="vertical">
          <Form.Item
            name="name"
            label="Asset Name"
            rules={[{ required: true, message: 'Please enter asset name' }]}
          >
            <Input placeholder="Enter asset name" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={4} placeholder="Enter asset description (optional)" />
          </Form.Item>
        </Form>
      </Modal>

      {data.length > 0 && (
        <Card title={`Results (${data.length} rows)`}>
          <Table
            columns={selectedColumns.map((colName) => ({
              title: colName,
              dataIndex: colName,
              key: colName,
              ellipsis: true,
            }))}
            dataSource={data}
            loading={loading}
            rowKey={(_record, index) => index!}
            pagination={{ pageSize: 50 }}
            scroll={{ x: true }}
          />
        </Card>
      )}
    </div>
  );
};

export default ObjectExplorer;
