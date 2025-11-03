import React, { useEffect, useState } from "react";
import { Card, Form, InputNumber, Button, message, Alert } from "antd";
import { getSettings, updateSettings, Settings } from "../api/settings";

export default function QuickSettings() {
  const [form] = Form.useForm<Settings>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then(settings => form.setFieldsValue(settings))
      .catch((e) => setError(e.message));
  }, [form]);

  const onFinish = async (values: Settings) => {
    setLoading(true);
    try {
      await updateSettings(values);
      message.success("Lưu cài đặt thành công!");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (error) return <Alert type="error" message={error} />;

  return (
    <Card title="Cài đặt nhanh">
      <Form form={form} layout="vertical" onFinish={onFinish}>
        <Form.Item label="Max hold M15" name="max_hold_m15" rules={[{ required: true, type: "number" }]}>
          <InputNumber min={1} />
        </Form.Item>
        <Form.Item label="Trailing Stop" name="trailing_stop" rules={[{ required: true, type: "number" }]}>
          <InputNumber min={0} step={0.0001} />
        </Form.Item>
        <Form.Item label="Snapshot Confirmations" name="snapshot_confirmations" rules={[{ required: true, type: "number" }]}>
          <InputNumber min={0} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>Lưu</Button>
        </Form.Item>
      </Form>
    </Card>
  );
}