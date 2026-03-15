import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Button,
  message,
  Empty,
  Spin,
  Modal,
  Typography,
  Space,
  Tag,
} from 'antd';
import {
  DeleteOutlined,
  ExclamationCircleOutlined,
  FolderOpenOutlined,
  CalendarOutlined,
  DatabaseOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import { assetService, Asset, AssetLineage } from '@/services/asset';
import LineageGraph from '@/components/LineageGraph';

const { Title, Text, Paragraph } = Typography;
const { confirm } = Modal;

const AssetList: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const projectId = id ? parseInt(id) : undefined;

  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(false);
  const [lineageModalOpen, setLineageModalOpen] = useState(false);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [lineageData, setLineageData] = useState<AssetLineage>({ upstream: [], downstream: [] });

  useEffect(() => {
    if (projectId) {
      loadAssets();
    }
  }, [projectId]);

  const loadAssets = async () => {
    if (!projectId) return;

    setLoading(true);
    try {
      const data = await assetService.listAssets(projectId);
      setAssets(data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load assets');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAsset = (asset: Asset) => {
    confirm({
      title: 'Delete Asset',
      icon: <ExclamationCircleOutlined />,
      content: `Are you sure you want to delete "${asset.name}"?`,
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        if (!projectId) return;
        try {
          await assetService.deleteAsset(projectId, asset.id);
          message.success('Asset deleted successfully');
          loadAssets();
        } catch (error: any) {
          message.error(error.response?.data?.detail || 'Failed to delete asset');
        }
      },
    });
  };

  const handleViewLineage = async (e: React.MouseEvent, asset: Asset) => {
    e.stopPropagation();
    if (!projectId) return;
    setSelectedAsset(asset);
    setLineageModalOpen(true);
    setLineageLoading(true);
    try {
      const data = await assetService.getLineage(projectId, asset.id);
      setLineageData(data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load lineage');
      setLineageData({ upstream: [], downstream: [] });
    } finally {
      setLineageLoading(false);
    }
  };

  const handleOpenAsset = (asset: Asset) => {
    navigate(`/projects/${projectId}/explorer`, {
      state: { assetConfig: asset.query_config },
    });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Card
        title={
          <Space>
            <FolderOpenOutlined />
            <span>Saved Assets</span>
          </Space>
        }
        extra={
          <Button type="primary" onClick={() => navigate(`/projects/${projectId}/explorer`)}>
            Back to Explorer
          </Button>
        }
      >
        {assets.length === 0 ? (
          <Empty
            description="No saved assets yet"
            style={{ padding: '60px 0' }}
          >
            <Button type="primary" onClick={() => navigate(`/projects/${projectId}/explorer`)}>
              Create Your First Asset
            </Button>
          </Empty>
        ) : (
          <Row gutter={[16, 16]}>
            {assets.map((asset) => (
              <Col xs={24} sm={12} lg={8} key={asset.id}>
                <Card
                  hoverable
                  onClick={() => handleOpenAsset(asset)}
                  style={{ height: '100%' }}
                  actions={[
                    <Button
                      type="text"
                      icon={<ApartmentOutlined />}
                      onClick={(e) => handleViewLineage(e, asset)}
                    >
                      查看血缘
                    </Button>,
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteAsset(asset);
                      }}
                    >
                      Delete
                    </Button>,
                  ]}
                >
                  <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <Title level={5} style={{ marginBottom: 8 }}>
                      {asset.name}
                    </Title>

                    <Tag color="blue">{asset.query_config.object_type}</Tag>

                    {asset.description && (
                      <Paragraph
                        ellipsis={{ rows: 2 }}
                        style={{ marginBottom: 8, color: '#666' }}
                      >
                        {asset.description}
                      </Paragraph>
                    )}

                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      {asset.row_count !== undefined && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          <DatabaseOutlined /> {asset.row_count} rows
                        </Text>
                      )}

                      <Text type="secondary" style={{ fontSize: 12 }}>
                        <CalendarOutlined /> {formatDate(asset.created_at)}
                      </Text>

                      {asset.query_config.filters && asset.query_config.filters.length > 0 && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {asset.query_config.filters.length} filter(s)
                        </Text>
                      )}

                      {asset.query_config.joins && asset.query_config.joins.length > 0 && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {asset.query_config.joins.length} join(s)
                        </Text>
                      )}
                    </Space>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Card>

      <Modal
        title={`数据血缘 - ${selectedAsset?.name}`}
        open={lineageModalOpen}
        onCancel={() => setLineageModalOpen(false)}
        footer={null}
        width={800}
      >
        {lineageLoading ? (
          <div style={{ textAlign: 'center', padding: '60px 0' }}>
            <Spin size="large" />
          </div>
        ) : (
          <LineageGraph
            assetName={selectedAsset?.name || ''}
            lineage={lineageData}
          />
        )}
      </Modal>
    </div>
  );
};

export default AssetList;
