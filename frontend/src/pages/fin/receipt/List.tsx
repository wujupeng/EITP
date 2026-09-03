import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space } from 'antd'
import { receiptApi } from '@/api/fin/receipt'
import { useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

const RECEIPT_STATUS = ['PENDING', 'CONFIRMED', 'WRITTEN_OFF', 'CANCELLED']

export default function ReceiptListPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await receiptApi.list(params)
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
    { title: '收款编号', dataIndex: 'receipt_number', key: 'receipt_number' },
    { title: '付款方', dataIndex: 'payer', key: 'payer' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'CONFIRMED' ? 'green' : v === 'WRITTEN_OFF' ? 'blue' : 'orange'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '到账日期', dataIndex: 'received_at', key: 'received_at' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/fin/receipts/${record.receipt_id}`)}>详情</Button>
    )},
  ]

  return (
    <Card title="收款单列表">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={RECEIPT_STATUS.map(s => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item name="payer" label="付款方">
          <Input placeholder="付款方" allowClear />
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
      <Table columns={columns} dataSource={data} rowKey="receipt_id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  )
}