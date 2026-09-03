import { useState } from 'react'
import { Card, Form, Input, Select, Button, message } from 'antd'
import { settlementApi } from '@/api/fin/settlement'
import { useNavigate } from 'react-router-dom'
import DecimalInput from '@/components/fin/DecimalInput'

const SETTLEMENT_TYPES = ['INTER_COMPANY', 'EXTERNAL', 'CROSS_TENANT']

export default function SettlementCreatePage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      const resp = await settlementApi.create(values)
      message.success('结算单创建成功')
      navigate(`/fin/settlements/${resp.data.settlement_id}`)
    } catch {
      message.error('结算单创建失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="创建结算单">
      <Form layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 600 }} initialValues={{ currency: 'CNY' }}>
        <Form.Item name="settlement_number" label="结算编号" rules={[{ required: true }]}>
          <Input placeholder="STL-2026-001" />
        </Form.Item>
        <Form.Item name="settlement_type" label="类型" rules={[{ required: true }]}>
          <Select options={SETTLEMENT_TYPES.map(t => ({ label: t, value: t }))} />
        </Form.Item>
        <Form.Item name="counterparty" label="交易方" rules={[{ required: true }]}>
          <Input placeholder="交易方名称" />
        </Form.Item>
        <Form.Item name="amount" label="金额" rules={[{ required: true }]}>
          <DecimalInput placeholder="0.00" />
        </Form.Item>
        <Form.Item name="currency" label="币种" rules={[{ required: true }]}>
          <Select options={['CNY', 'USD', 'EUR', 'GBP'].map(c => ({ label: c, value: c }))} />
        </Form.Item>
        <Form.Item name="remark" label="备注">
          <Input.TextArea rows={3} />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>提交</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}