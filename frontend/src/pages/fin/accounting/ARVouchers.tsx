import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space } from 'antd'
import { accountingApi } from '@/api/fin/accounting'
import { useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

const VOUCHER_STATUS = ['DRAFT', 'POSTED', 'REVERSED']

export default function ARVouchersPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await accountingApi.arVouchers.list(params)
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
    { title: '凭证号', dataIndex: 'voucher_number', key: 'voucher_number' },
    { title: '客户', dataIndex: 'customer', key: 'customer' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'POSTED' ? 'green' : v === 'REVERSED' ? 'red' : 'orange'}>{v}</Tag> },
    { title: '应收金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '账期', dataIndex: 'period', key: 'period' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/fin/accounting/ar-vouchers/${record.voucher_id}`)}>详情</Button>
    )},
  ]

  return (
    <Card title="应收凭证列表">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={VOUCHER_STATUS.map(s => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item name="customer" label="客户">
          <Input placeholder="客户" allowClear />
        </Form.Item>
        <Form.Item name="period" label="账期">
          <Input placeholder="YYYY-MM" allowClear />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
      <Table columns={columns} dataSource={data} rowKey="voucher_id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  )
}