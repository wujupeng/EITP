import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space } from 'antd'
import { reconciliationApi } from '@/api/fin/reconciliation'
import { useNavigate } from 'react-router-dom'

const RECON_STATUS = ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'HAS_DIFFERENCE']

export default function ReconciliationListPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await reconciliationApi.list(params)
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
    { title: '批次号', dataIndex: 'batch_number', key: 'batch_number' },
    { title: '对账类型', dataIndex: 'recon_type', key: 'recon_type', render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'COMPLETED' ? 'green' : v === 'HAS_DIFFERENCE' ? 'red' : 'orange'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '匹配数', dataIndex: 'matched_count', key: 'matched_count' },
    { title: '差异数', dataIndex: 'diff_count', key: 'diff_count' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/fin/reconciliations/${record.recon_id}`)}>详情</Button>
    )},
  ]

  return (
    <Card title="对账批次列表">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 160 }} options={RECON_STATUS.map(s => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item name="recon_type" label="对账类型">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={['BANK', 'INTER_COMPANY', 'TENANT'].map(t => ({ label: t, value: t }))} />
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
      <Table columns={columns} dataSource={data} rowKey="recon_id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  )
}