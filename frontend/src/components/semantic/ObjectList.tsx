import React from 'react';
import { List, Typography } from 'antd';
import { DatabaseOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface ObjectListProps {
  objects: string[];
  selected: string | null;
  onSelect: (name: string) => void;
}

const ObjectList: React.FC<ObjectListProps> = ({ objects, selected, onSelect }) => {
  return (
    <List
      size="small"
      dataSource={objects}
      renderItem={name => (
        <List.Item
          onClick={() => onSelect(name)}
          style={{
            cursor: 'pointer',
            backgroundColor: selected === name ? '#e6f7ff' : undefined,
            padding: '8px 16px',
          }}
        >
          <DatabaseOutlined style={{ marginRight: 8, color: '#1890ff' }} />
          <Text strong={selected === name}>{name}</Text>
        </List.Item>
      )}
    />
  );
};

export default ObjectList;
