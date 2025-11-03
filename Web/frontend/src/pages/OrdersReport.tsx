import React, { useEffect, useState } from "react";
import { Table, Alert, Input } from "antd";
import { getOrders, Order } from "../api/orders";

export default function OrdersReport() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [symbol, setSymbol] = useState<string | undefined>(undefined);

  const fetchData = () =>
    getOrders(page, pageSize, symbol)
      .then(data => { setOrders(data.orders); setTotal(data.total); })
      .catch(e => setError(e.message));

  useEffect(() => { fetchData(); }, [page, pageSize, symbol]);

  return (
    <>
      <Input.Search placeholder="Lọc theo symbol..." onSearch={val => setSymbol(val || undefined)} style={{ width: 200, marginBottom: 12 }} />
      {error && <Alert type="error" message={error} />}
      <Table
        dataSource={orders}
        rowKey="id"
        pagination={{
          current: page, pageSize, total,
          onChange: (p, ps) => { setPage(p); setPageSize(ps); },
        }}
        columns={[
          { title: "ID", dataIndex: "id" },
          { title: "Symbol", dataIndex: "symbol" },
          { title: "Side", dataIndex: "side" },
          { title: "PnL", dataIndex: "pnl" },
          { title: "Status", dataIndex: "status" },
        ]}
      />
    </>
  );
}