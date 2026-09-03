import { useState } from 'react'
import { Card, Form, Input, Select, Button, message } from 'antd'
import { paymentApi } from '@/api/fin/payment'
import { useNavigate } from 'react-router-dom'
import DecimalInput from '@/components/fin/DecimalInput'

export default function PaymentRequestPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      const resp = await paymentApi.request(values)
      message.success('付款申请已提交')
      navigate(`/fin/payments/${resp.data.payment_id}`)
    } catch {
      message.error('付款申请失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="付款申请">
      <Form layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 600 }} initialValues={{ currency: 'CNY' }}>
        <Form.Item name="payment_number" label="付款编号" rules={[{ required: true }]}>
          <Input placeholder="PAY-2026-001" />
        </Form.Item>
        <Form.Item name="payee" label="收款方" rules={[{ required: true }]}>
          <Input placeholder="收款方名称" />
        </Form.Item>
        <Form.Item name="payee_account" label="收款账户" rules={[{ required: true }]}>
          <Input placeholder="银行账号" />
        </Form.Item>
        <Form.Item name="amount" label="金额" rules={[{ required: true }]}>
          <DecimalInput placeholder="0.00" />
        </Form.Item>
        <Form.Item name="currency" label="币种" rules={[{ required: true }]}>
          <Select options={['CNY', 'USD', 'EUR', 'GBP'].map(c => ({ label: c, value: c }))} />
        </Form.Item>
        <Form.Item name="purpose" label="付款用途">
          <Input placeholder="货款/服务费/其他" />
        </Form.Item>
        <Form.Item name="remark" label="备注">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>提交申请</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}