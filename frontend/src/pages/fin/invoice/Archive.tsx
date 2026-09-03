import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space, message } from 'antd'
import { invoiceApi } from '@/api/fin/invoice'
import { useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function InvoiceArchivePage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await invoiceApi.list({ ...params, status: 'ARCHIVED' })
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

  const handleArchive = async (id: string) => {
    try {
      await invoiceApi.archive(id)
      message.success('归档成功')
      fetchData()
    } catch {
      message.error('归档失败')
    }
  }

  const columns = [
    { title: '发票号', dataIndex: 'invoice_number', key: 'invoice_number' },
    { title: '购方', dataIndex: 'buyer', key: 'buyer' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'ARCHIVED' ? 'default' : 'blue'}>{v}</Tag> },
    { title: '金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '归档时间', dataIndex: 'archived_at', key: 'archived_at' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Space>
        <Button type="link" onClick={() => navigate(`/fin/invoices/${record.invoice_id}`)}>详情</Button>
        {record.status !== 'ARCHIVED' && <Button type="link" onClick={() => handleArchive(record.invoice_id)}>归档</Button>}
      </Space>
    )},
  ]

  return (
    <Card title="发票归档管理">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="invoice_number" label="发票号">
          <Input placeholder="发票号" allowClear />
        </Form.Item>
        <Form.Item name="buyer" label="购方">
          <Input placeholder="购方" allowClear />
        </Form.Item>
        <Form.Item name="period" label="账期">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={['2026-08', '2026-07', '2026-06'].map(p => ({ label: p, value: p }))} />
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