import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space } from 'antd'
import { settlementApi } from '@/api/fin/settlement'
import { useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

const SETTLEMENT_TYPES = ['INTER_COMPANY', 'EXTERNAL', 'CROSS_TENANT']
const SETTLEMENT_STATUS = ['DRAFT', 'PENDING', 'CONFIRMED', 'CANCELLED']

export default function SettlementListPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await settlementApi.list(params)
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
    { title: '结算编号', dataIndex: 'settlement_number', key: 'settlement_number' },
    { title: '类型', dataIndex: 'settlement_type', key: 'settlement_type', render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'CONFIRMED' ? 'green' : v === 'CANCELLED' ? 'red' : 'orange'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '交易方', dataIndex: 'counterparty', key: 'counterparty' },
    { title: '金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/fin/settlements/${record.settlement_id}`)}>详情</Button>
    )},
  ]

  return (
    <Card title="结算单列表" extra={<Button type="primary" onClick={() => navigate('/fin/settlements/create')}>创建结算单</Button>}>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="settlement_type" label="类型">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={SETTLEMENT_TYPES.map(t => ({ label: t, value: t }))} />
        </Form.Item>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={SETTLEMENT_STATUS.map(s => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item name="counterparty" label="交易方">
          <Input placeholder="交易方" allowClear />
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
      <Table columns={columns} dataSource={data} rowKey="settlement_id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  )
}