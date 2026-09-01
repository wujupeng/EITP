import { useState, useEffect } from 'react'
import { Card, Form, Switch, Input, Button, message } from 'antd'
import { secApi } from '@/api/sec'

export default function SecConfigPage() {
  const [form] = Form.useForm()

  useEffect(() => {
    secApi.getConfig().then(resp => form.setFieldsValue(resp.data))
  }, [form])

  const handleSave = async () => {
    const values = await form.validateFields()
    try {
      await secApi.updateConfig(values)
      message.success('配置已保存')
    } catch { message.error('保存失败') }
  }

  return (
    <Card title="认证配置" extra={<Button type="primary" onClick={handleSave}>保存</Button>}>
      <Form form={form} layout="vertical">
        <Form.Item name="strict_mode" label="严格模式" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item name="report_retention_days" label="报告保留天数">
          <Input type="number" />
        </Form.Item>
      </Form>
    </Card>
  )
}