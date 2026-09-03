import { useState } from 'react'
import { Card, Form, Input, Select, Button, message } from 'antd'
import { invoiceApi } from '@/api/fin/invoice'
import { useNavigate } from 'react-router-dom'
import DecimalInput from '@/components/fin/DecimalInput'

export default function InvoiceIssuePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      const resp = await invoiceApi.issue(values)
      message.success('发票开具成功')
      navigate(`/fin/invoices/${resp.data.invoice_id}`)
    } catch {
      message.error('发票开具失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="发票开具">
      <Form layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 600 }} initialValues={{ currency: 'CNY', invoice_type: 'NORMAL' }}>
        <Form.Item name="invoice_number" label="发票号" rules={[{ required: true }]}>
          <Input placeholder="INV-2026-001" />
        </Form.Item>
        <Form.Item name="invoice_type" label="发票类型" rules={[{ required: true }]}>
          <Select options={['NORMAL', 'SPECIAL', 'ELECTRONIC'].map(t => ({ label: t, value: t }))} />
        </Form.Item>
        <Form.Item name="buyer" label="购方" rules={[{ required: true }]}>
          <Input placeholder="购方名称" />
        </Form.Item>
        <Form.Item name="seller" label="销方" rules={[{ required: true }]}>
          <Input placeholder="销方名称" />
        </Form.Item>
        <Form.Item name="amount" label="金额" rules={[{ required: true }]}>
          <DecimalInput placeholder="0.00" />
        </Form.Item>
        <Form.Item name="tax_rate" label="税率" rules={[{ required: true }]}>
          <Input placeholder="0.13" />
        </Form.Item>
        <Form.Item name="currency" label="币种" rules={[{ required: true }]}>
          <Select options={['CNY', 'USD', 'EUR'].map(c => ({ label: c, value: c }))} />
        </Form.Item>
        <Form.Item name="remark" label="备注">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>开具发票</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}