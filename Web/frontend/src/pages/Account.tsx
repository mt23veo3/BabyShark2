import { Card, Button } from 'antd';
import { useAuth } from '../context/AuthContext';

export default function Account() {
  const { user, logout } = useAuth();
  return (
    <Card title="Tài khoản">
      <p>Tên đăng nhập: {user}</p>
      <Button onClick={logout}>Đăng xuất</Button>
    </Card>
  );
}