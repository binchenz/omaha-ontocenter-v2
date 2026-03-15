import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Select, Button, Table, message, Space, Form, Input } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { queryService } from '@/services/query';

const { Option } = Select;

const ObjectExplorer: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [objectTypes, setObjectTypes] = useState<string[]>([]);
  const [selectedType, setSelectedType] = useState<string>('');
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [columns, setColumns] = useState<any[]>([]);

  useEffect(() => {
    loadObjectTypes();
  }, [id]);

  const loadObjectTypes = async () => {
    if (!id) return;
    try {
      const result = await queryService.listObjectTypes(parseInt(id));
      setObjectTypes(result.objects);
    } catch (error: any) {
      message.error('Failed to load object types');
    }
  };

  const handleQuery = async (filters?: any) => {
    if (!id || !selectedType) return;
    setLoading(true);
    try {
      const result = await queryService.queryObjects(
        parseInt(id),
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
    </Card>
  );
};

export default ObjectExplorer;
