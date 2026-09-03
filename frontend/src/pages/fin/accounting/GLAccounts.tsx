import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space, Modal, message } from 'antd'
import { accountingApi } from '@/api/fin/accounting'

export default function GLAccountsPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await accountingApi.glAccounts.list(params)
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

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      await accountingApi.glAccounts.create(values)
      message.success('科目创建成功')
      setModalOpen(false)
      form.resetFields()
      fetchData()
    } catch {
      message.error('科目创建失败')
    }
  }

  const columns = [
    { title: '科目编码', dataIndex: 'account_code', key: 'account_code' },
    { title: '科目名称', dataIndex: 'account_name', key: 'account_name' },
    { title: '科目类别', dataIndex: 'account_type', key: 'account_type', render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: '余额方向', dataIndex: 'balance_direction', key: 'balance_direction', render: (v: string) => <Tag color={v === 'DEBIT' ? 'green' : 'red'}>{v}</Tag> },
    { title: '上级科目', dataIndex: 'parent_code', key: 'parent_code' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'ACTIVE' ? 'green' : 'default'}>{v}</Tag> },
  ]

  return (
    <Card title="总账科目管理" extra={<Button type="primary" onClick={() => setModalOpen(true)}>新增科目</Button>}>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="account_type" label="科目类别">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'].map(t => ({ label: t, value: t }))} />
        </Form.Item>
        <Form.Item name="account_code" label="科目编码">
          <Input placeholder="科目编码" allowClear />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
      <Table columns={columns} dataSource={data} rowKey="account_code" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新增科目" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="account_code" label="科目编码" rules={[{ required: true }]}>
            <Input placeholder="1001" />
          </Form.Item>
          <Form.Item name="account_name" label="科目名称" rules={[{ required: true }]}>
            <Input placeholder="库存现金" />
          </Form.Item>
          <Form.Item name="account_type" label="科目类别" rules={[{ required: true }]}>
            <Select options={['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'].map(t => ({ label: t, value: t }))} />
          </Form.Item>
          <Form.Item name="balance_direction" label="余额方向" rules={[{ required: true }]}>
            <Select options={[{ label: '借', value: 'DEBIT' }, { label: '贷', value: 'CREDIT' }]} />
          </Form.Item>
          <Form.Item name="parent_code" label="上级科目">
            <Input placeholder="上级科目编码" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}