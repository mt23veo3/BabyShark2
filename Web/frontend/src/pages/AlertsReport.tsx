import React, { useEffect, useState } from "react";
import { List, Card, Alert as AntdAlert, Pagination } from "antd";
import { getAlerts, Alert as AlertType } from "../api/alerts";
import { useSocket } from "../hooks/useSocket";

export default function AlertsReport() {
  const [alerts, setAlerts] = useState<AlertType[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAlerts(page, pageSize)
      .then(data => { setAlerts(data.alerts); setTotal(data.total); })
      .catch(e => setError(e.message));
  }, [page, pageSize]);

  useSocket("alerts_update", (alert: AlertType) => {
    setAlerts(prev => [alert, ...prev]);
    setTotal(t => t + 1);
  });

  return (
    <Card title="Báo cáo Cảnh báo">
      {error && <AntdAlert type="error" message={error} />}
      <List
        dataSource={alerts}
        renderItem={alert => (
          <List.Item>
            <span style={{ color: alert.level === "warn" ? "red" : "blue" }}>[{alert.level.toUpperCase()}]</span> {alert.msg}
            <span style={{ float: "right", color: "#999" }}>{alert.time}</span>
          </List.Item>
        )}
      />
      <Pagination
        style={{ marginTop: 16 }}
        current={page}
        pageSize={pageSize}
        total={total}
        onChange={(p, ps) => { setPage(p); setPageSize(ps); }}
      />
    </Card>
  );
}