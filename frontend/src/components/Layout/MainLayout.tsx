import React from 'react';
import { Layout, Menu } from 'antd';
import { ProjectOutlined, LogoutOutlined } from '@ant-design/icons';
import { useNavigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

const { Header, Content } = Layout;

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
          Omaha OntoCenter
        </div>
        <Menu
          theme="dark"
          mode="horizontal"
          selectedKeys={[]}
          items={[
            {
              key: 'projects',
              icon: <ProjectOutlined />,
              label: 'Projects',
              onClick: () => navigate('/projects'),
            },
            {
              key: 'user',
              label: user?.username,
              children: [
                {
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  label: 'Logout',
                  onClick: handleLogout,
                },
              ],
            },
          ]}
        />
      </Header>
      <Content style={{ padding: '24px', background: '#f0f2f5' }}>
        <Outlet />
      </Content>
    </Layout>
  );
};

export default MainLayout;
