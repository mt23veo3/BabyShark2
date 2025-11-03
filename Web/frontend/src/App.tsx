import React, { useState } from 'react';
import { Layout } from 'antd';
import SidebarMenu from './components/SidebarMenu';
import routes from './routes';
import { AuthProvider } from './context/AuthContext';

const { Header, Sider, Content } = Layout;

const App: React.FC = () => {
  const [selectedPage, setSelectedPage] = useState('dashboard');
  const PageComponent = routes[selectedPage];

  return (
    <AuthProvider>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider width={220}>
          <SidebarMenu onSelect={setSelectedPage} />
        </Sider>
        <Layout>
          <Header style={{ background: "#fff", fontSize: 22 }}>
            🐬 BabyShark Dashboard
          </Header>
          <Content style={{ margin: 24, background: "#fff" }}>
            <PageComponent />
          </Content>
        </Layout>
      </Layout>
    </AuthProvider>
  );
};

export default App;