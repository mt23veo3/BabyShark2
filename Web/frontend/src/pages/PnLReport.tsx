import React, { useEffect, useState } from "react";
import { Card, Alert } from "antd";
import { getPnLReport, PnLData } from "../api/pnl";

export default function PnLReport() {
  const [data, setData] = useState<PnLData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPnLReport().then(setData).catch(e => setError(e.message));
  }, []);

  if (error) return <Alert type="error" message={error} />;
  if (!data) return <div>Đang tải dữ liệu...</div>;

  return (
    <Card title="Lợi nhuận theo ngày">
      <ul>
        {data.labels.map((label, i) => (
          <li key={label}>{label}: {data.values[i]}</li>
        ))}
      </ul>
    </Card>
  );
}