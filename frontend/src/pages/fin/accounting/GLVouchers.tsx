import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space, Modal, message } from 'antd'
import { accountingApi } from '@/api/fin/accounting'
import { useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

const VOUCHER_STATUS = ['DRAFT', 'POSTED', 'REVERSED']

export default function GLVouchersPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const [form] = Form.useForm()
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await accountingApi.glVouchers.list(params)
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
      const values = await createForm.validateFields()
      await accountingApi.glVouchers.create(values)
      message.success('凭证创建成功')
      setCreateOpen(false)
      createForm.resetFields()
      fetchData()
    } catch {
      message.error('凭证创建失败')
    }
  }

  const columns = [
    { title: '凭证号', dataIndex: 'voucher_number', key: 'voucher_number' },
    { title: '摘要', dataIndex: 'summary', key: 'summary' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'POSTED' ? 'green' : v === 'REVERSED' ? 'red' : 'orange'}>{v}</Tag> },
    { title: '借方合计', dataIndex: 'debit_total', key: 'debit_total', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '贷方合计', dataIndex: 'credit_total', key: 'credit_total', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '账期', dataIndex: 'period', key: 'period' },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => navigate(`/fin/accounting/gl-vouchers/${record.voucher_id}`)}>详情</Button>
    )},
  ]

  return (
    <Card title="总账凭证列表" extra={<Button type="primary" onClick={() => setCreateOpen(true)}>新增凭证</Button>}>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={VOUCHER_STATUS.map(s => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item name="period" label="账期">
          <Input placeholder="YYYY-MM" allowClear />
        </Form.Item>
        <Form.Item name="voucher_number" label="凭证号">
          <Input placeholder="凭证号" allowClear />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
      <Table columns={columns} dataSource={data} rowKey="voucher_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新增凭证" open={createOpen} onOk={handleCreate} onCancel={() => setCreateOpen(false)} width={600}>
        <Form form={createForm} layout="vertical">
          <Form.Item name="voucher_number" label="凭证号" rules={[{ required: true }]}>
            <Input placeholder="GL-2026-001" />
          </Form.Item>
          <Form.Item name="period" label="账期" rules={[{ required: true }]}>
            <Input placeholder="2026-09" />
          </Form.Item>
          <Form.Item name="summary" label="摘要" rules={[{ required: true }]}>
            <Input placeholder="凭证摘要" />
          </Form.Item>
          <Form.Item name="currency" label="币种" rules={[{ required: true }]} initialValue="CNY">
            <Select options={['CNY', 'USD', 'EUR'].map(c => ({ label: c, value: c }))} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}