import { List, Tag } from 'antd';

const notifications = [
  { level: 'info', msg: 'Đã vào lệnh BTC/USDT', time: '13:10' },
  { level: 'warn', msg: 'Giữ lệnh quá lâu', time: '12:50' },
];

export default function NotificationBar() {
  return (
    <List
      size="small"
      header={<strong>Thông báo mới nhất</strong>}
      dataSource={notifications}
      renderItem={item => (
        <List.Item>
          <Tag color={item.level === 'warn' ? 'red' : 'blue'}>{item.level.toUpperCase()}</Tag>
          {item.msg} <span style={{ float: 'right', color: '#bbb' }}>{item.time}</span>
        </List.Item>
      )}
    />
  );
}