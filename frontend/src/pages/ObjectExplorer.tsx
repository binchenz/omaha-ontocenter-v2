import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
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
} from 'antd';
import { SearchOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { queryService } from '@/services/query';

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

const ObjectExplorer: React.FC<ObjectExplorerProps> = ({ projectId: propProjectId }) => {
  const { id } = useParams<{ id: string }>();
  const projectId = propProjectId || (id ? parseInt(id) : undefined);

  // State
  const [objectTypes, setObjectTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [allColumns, setAllColumns] = useState<Column[]>([]);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [filters, setFilters] = useState<Filter[]>([]);
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [tableColumns, setTableColumns] = useState<any[]>([]);

  useEffect(() => {
    loadObjectTypes();
  }, [projectId]);

  useEffect(() => {
    if (selectedType) {
      loadObjectSchema();
    }
  }, [selectedType]);

  const loadObjectTypes = async () => {
    if (!projectId) return;
    try {
      const result = await queryService.listObjectTypes(projectId);
      setObjectTypes(result.objects || []);
    } catch (error: any) {
      message.error('Failed to load object types');
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
        100
      );

      if (result.success && result.data) {
        setData(result.data);
        const cols = selectedColumns.map((colName) => ({
          title: colName,
          dataIndex: colName,
          key: colName,
          ellipsis: true,
        }));
        setTableColumns(cols);
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

  const selectAllColumns = () => {
    setSelectedColumns(allColumns.map((col) => col.name));
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
              <Button
                type="primary"
                icon={<SearchOutlined />}
                onClick={handleQuery}
                disabled={!selectedType || selectedColumns.length === 0}
                loading={loading}
                block
              >
                Query
              </Button>
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

      {data.length > 0 && (
        <Card title={`Results (${data.length} rows)`}>
          <Table
            columns={tableColumns}
            dataSource={data}
            loading={loading}
            rowKey={(record, index) => index}
            pagination={{ pageSize: 50 }}
            scroll={{ x: true }}
          />
        </Card>
      )}
    </div>
  );
};

export default ObjectExplorer;
