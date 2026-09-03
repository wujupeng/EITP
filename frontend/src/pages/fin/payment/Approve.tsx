import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Form, Input, Button, message, Alert } from 'antd'
import { paymentApi } from '@/api/fin/payment'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function PaymentApprovePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [payment, setPayment] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    if (id) paymentApi.get(id).then(resp => setPayment(resp.data))
  }, [id])

  const handleApprove = async () => {
    setLoading(true)
    try {
      const values = await form.validateFields()
      await paymentApi.approve(id!, values)
      message.success('付款审批通过')
      navigate(`/fin/payments/${id}`)
    } catch {
      message.error('付款审批失败')
    } finally {
      setLoading(false)
    }
  }

  if (!payment) return <Card title="付款审批">加载中...</Card>

  return (
    <Card title="付款审批">
      <Alert message="请仔细核对付款信息后审批" type="warning" showIcon style={{ marginBottom: 16 }} />
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="付款编号">{payment.payment_number}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{payment.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="收款方">{payment.payee}</Descriptions.Item>
        <Descriptions.Item label="金额">{formatMoney(payment.amount, payment.currency)}</Descriptions.Item>
      </Descriptions>
      <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
        <Form.Item name="approver" label="审批人" rules={[{ required: true }]}>
          <Input placeholder="审批人账号" />
        </Form.Item>
        <Form.Item name="decision" label="审批意见">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" loading={loading} onClick={handleApprove}>审批通过</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}