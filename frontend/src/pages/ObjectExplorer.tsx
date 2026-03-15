import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Select, Button, Table, message, Space, Form, Input } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { queryService } from '@/services/query';

const { Option } = Select;

interface ObjectExplorerProps {
  projectId?: number;
}

const ObjectExplorer: React.FC<ObjectExplorerProps> = ({ projectId: propProjectId }) => {
  const { id } = useParams<{ id: string }>();
  const projectId = propProjectId || (id ? parseInt(id) : undefined);
  const [objectTypes, setObjectTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [columns, setColumns] = useState<any[]>([]);
  const [allColumns, setAllColumns] = useState<string[]>([]);
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [filters, setFilters] = useState<Array<{ field: string; operator: string; value: string }>>([]);

  useEffect(() => {
    loadObjectTypes();
  }, [projectId]);

  const loadObjectTypes = async () => {
    if (!projectId) {
      console.log('No project ID');
      return;
    }
    console.log('Loading object types for project:', projectId);
    try {
      const result = await queryService.listObjectTypes(projectId);
      console.log('Object types loaded:', result);
      setObjectTypes(result.objects || []);
      if (!result.objects || result.objects.length === 0) {
        message.warning('No object types found. Please configure the project ontology.');
      }
    } catch (error: any) {
      console.error('Failed to load object types:', error);
      console.error('Error response:', error.response);
      message.error(`Failed to load object types: ${error.message}`);
    }
  };

  const handleQuery = async (filters?: any) => {
    if (!projectId || !selectedType) return;
    setLoading(true);
    try {
      const result = await queryService.queryObjects(
        projectId,
        selectedType,
        filters
      );
      if (result.success && result.data) {
        setData(result.data);
        // Generate columns from first row
        if (result.data.length > 0) {
          const cols = Object.keys(result.data[0]).map((key) => ({
            title: key,
            dataIndex: key,
            key: key,
          }));
          setColumns(cols);
        }
      } else {
        message.error(result.error || 'Query failed');
      }
    } catch (error: any) {
      message.error('Failed to query objects');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card title="Object Explorer">
      {objectTypes.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>
          <p>Object Explorer will be available here after configuration is saved.</p>
          <p style={{ color: '#999', marginTop: '10px' }}>
            Please configure the project's Omaha ontology to enable object exploration.
          </p>
        </div>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <Space>
            <Select
              style={{ width: 200 }}
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
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={() => handleQuery()}
              disabled={!selectedType}
            >
              Query
            </Button>
          </Space>

          <Table
            columns={columns}
            dataSource={data}
            loading={loading}
            rowKey={(record, index) => index}
            pagination={{ pageSize: 50 }}
          />
        </Space>
      )}
    </Card>
  );
};

export default ObjectExplorer;
