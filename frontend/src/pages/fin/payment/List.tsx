import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space } from 'antd'
import { paymentApi } from '@/api/fin/payment'
import { useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

const PAYMENT_STATUS = ['DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'EXECUTING', 'COMPLETED', 'REJECTED']

export default function PaymentListPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await paymentApi.list(params)
      setData(res.data?.items || [])
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleSearch = async () => {
    const values = await form.validateFields()
    fetchData(values)
  }

  const handleReset = () => {
    form.resetFields()
    fetchData()
  }

  const columns = [
    { title: '付款编号', dataIndex: 'payment_number', key: 'payment_number' },
    { title: '收款方', dataIndex: 'payee', key: 'payee' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'COMPLETED' ? 'green' : v === 'REJECTED' ? 'red' : 'blue'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '申请日期', dataIndex: 'requested_at', key: 'requested_at' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/fin/payments/${record.payment_id}`)}>详情</Button>
    )},
  ]

  return (
    <Card title="付款单列表" extra={<Button type="primary" onClick={() => navigate('/fin/payments/request')}>付款申请</Button>}>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 160 }} options={PAYMENT_STATUS.map(s => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item name="payee" label="收款方">
          <Input placeholder="收款方" allowClear />
        </Form.Item>
        <Form.Item name="date_from" label="开始日期">
          <Input placeholder="YYYY-MM-DD" allowClear />
        </Form.Item>
        <Form.Item name="date_to" label="结束日期">
          <Input placeholder="YYYY-MM-DD" allowClear />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
      <Table columns={columns} dataSource={data} rowKey="payment_id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  )
}