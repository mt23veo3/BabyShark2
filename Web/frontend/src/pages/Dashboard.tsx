import React, { useEffect, useState } from "react";
import { Card, Statistic, Row, Col, Alert as AntdAlert, List, notification } from "antd";
import { getDashboardOverview } from "../api/dashboard";
import { getAlerts, Alert as AlertType } from "../api/alerts";
import { useSocket } from "../hooks/useSocket";

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardOverview().then(setData).catch(e => setError(e.message));
    getAlerts().then(res => setAlerts(res.alerts)).catch(() => {});
  }, []);

  useSocket("alerts_update", (alert: AlertType) => {
    setAlerts(prev => [alert, ...prev]);
    notification.warning({ message: "Cảnh báo mới", description: alert.msg });
  });

  if (error) return <AntdAlert type="error" message={error} />;
  if (!data) return <div>Đang tải dữ liệu...</div>;
  return (
    <div>
      <Row gutter={16}>
        <Col span={6}><Card><Statistic title="Balance" value={data.balance} precision={2} /></Card></Col>
        <Col span={6}><Card><Statistic title="PnL hôm nay" value={data.pnl_today} precision={2} /></Card></Col>
        <Col span={6}><Card><Statistic title="Lệnh đang mở" value={data.orders_open} /></Card></Col>
        <Col span={6}><Card><Statistic title="Tỉ lệ thắng" value={Math.round(data.orders_win_rate * 100)} suffix="%" /></Card></Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 24 }}>
        <Col span={16}><Card title="Biểu đồ giá (Demo)">
          <div style={{ height: 200, background: "#f5f5f5" }} />
        </Card></Col>
        <Col span={8}><Card title="Cảnh báo mới nhất">
          <List
            dataSource={alerts}
            renderItem={alert => (
              <List.Item>
                <span style={{ color: alert.level === "warn" ? "red" : "blue" }}>[{alert.level.toUpperCase()}]</span> {alert.msg}
                <span style={{ float: "right", color: "#999" }}>{alert.time}</span>
              </List.Item>
            )}
          />
        </Card></Col>
      </Row>
    </div>
  );
}