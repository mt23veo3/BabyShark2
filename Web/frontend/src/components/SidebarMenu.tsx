import React from "react";
import { Menu } from "antd";
import {
  DashboardOutlined, LineChartOutlined, TableOutlined,
  AlertOutlined, SettingOutlined, UserOutlined, ThunderboltOutlined,
} from "@ant-design/icons";

interface SidebarMenuProps { onSelect: (key: string) => void; }
const items = [
  { key: "dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
  { key: "pnl", icon: <LineChartOutlined />, label: "PnL" },
  { key: "orders", icon: <TableOutlined />, label: "Orders" },
  { key: "signals", icon: <ThunderboltOutlined />, label: "Signals" },
  { key: "alerts", icon: <AlertOutlined />, label: "Alerts" },
  { key: "settings", icon: <SettingOutlined />, label: "Settings" },
  { key: "account", icon: <UserOutlined />, label: "Account" },
];
export default function SidebarMenu({ onSelect }: SidebarMenuProps) {
  return (
    <Menu
      mode="inline"
      defaultSelectedKeys={["dashboard"]}
      style={{ height: "100%", borderRight: 0 }}
      items={items}
      onClick={({ key }) => onSelect(key)}
    />
  );
}