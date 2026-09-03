import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space } from 'antd'
import { invoiceApi } from '@/api/fin/invoice'
import { useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

const INVOICE_STATUS = ['DRAFT', 'ISSUED', 'VERIFIED', 'MATCHED', 'ARCHIVED', 'VOID']

export default function InvoiceListPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await invoiceApi.list(params)
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
    { title: '发票号', dataIndex: 'invoice_number', key: 'invoice_number' },
    { title: '购方', dataIndex: 'buyer', key: 'buyer' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'VERIFIED' ? 'green' : v === 'VOID' ? 'red' : v === 'ARCHIVED' ? 'default' : 'blue'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '开票日期', dataIndex: 'issued_at', key: 'issued_at' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/fin/invoices/${record.invoice_id}`)}>详情</Button>
    )},
  ]

  return (
    <Card title="发票列表" extra={<Button type="primary" onClick={() => navigate('/fin/invoices/issue')}>发票开具</Button>}>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={INVOICE_STATUS.map(s => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item name="buyer" label="购方">
          <Input placeholder="购方" allowClear />
        </Form.Item>
        <Form.Item name="invoice_type" label="发票类型">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={['NORMAL', 'SPECIAL', 'ELECTRONIC'].map(t => ({ label: t, value: t }))} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
      <Table columns={columns} dataSource={data} rowKey="invoice_id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  )
}