import React, { useEffect, useState } from "react";
import { Table, Alert, Input } from "antd";
import { getSignals, Signal } from "../api/signals";

export default function SignalsReport() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [symbol, setSymbol] = useState<string | undefined>(undefined);

  useEffect(() => {
    getSignals(page, pageSize, symbol)
      .then(data => { setSignals(data.signals); setTotal(data.total); })
      .catch(e => setError(e.message));
  }, [page, pageSize, symbol]);

  return (
    <>
      <Input.Search placeholder="Lọc theo symbol..." onSearch={val => setSymbol(val || undefined)} style={{ width: 200, marginBottom: 12 }} />
      {error && <Alert type="error" message={error} />}
      <Table
        dataSource={signals}
        rowKey="time"
        pagination={{
          current: page, pageSize, total,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
        columns={[
          { title: "Time", dataIndex: "time" },
          { title: "Symbol", dataIndex: "symbol" },
          { title: "Signal", dataIndex: "signal" },
        ]}
      />
    </>
  );
}