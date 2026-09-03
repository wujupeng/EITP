import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space, message } from 'antd'
import { collectionTaskApi } from '@/api/fin/receipt'
import { formatMoney } from '@/utils/finMoney'

const TASK_STATUS = ['PENDING', 'IN_PROGRESS', 'RESOLVED', 'ESCALATED']

export default function CollectionListPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await collectionTaskApi.list(params)
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

  const handleAction = async (id: string, action: string) => {
    try {
      await collectionTaskApi.handle(id, { action })
      message.success('操作成功')
      fetchData()
    } catch {
      message.error('操作失败')
    }
  }

  const columns = [
    { title: '任务编号', dataIndex: 'task_number', key: 'task_number' },
    { title: '客户', dataIndex: 'customer', key: 'customer' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'RESOLVED' ? 'green' : v === 'ESCALATED' ? 'red' : 'orange'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '应收金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '逾期天数', dataIndex: 'overdue_days', key: 'overdue_days' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Space>
        <Button type="link" onClick={() => handleAction(record.task_id, 'REMIND')}>催收</Button>
        <Button type="link" onClick={() => handleAction(record.task_id, 'ESCALATE')}>升级</Button>
      </Space>
    )},
  ]

  return (
    <Card title="催收任务列表">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={TASK_STATUS.map(s => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item name="customer" label="客户">
          <Input placeholder="客户" allowClear />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
      <Table columns={columns} dataSource={data} rowKey="task_id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  )
}