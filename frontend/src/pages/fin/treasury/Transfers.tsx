import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space, Modal, message } from 'antd'
import { treasuryApi } from '@/api/fin/treasury'
import { formatMoney } from '@/utils/finMoney'
import DecimalInput from '@/components/fin/DecimalInput'

const TRANSFER_STATUS = ['PENDING', 'APPROVED', 'EXECUTED', 'REJECTED']

export default function TreasuryTransfersPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const [createForm] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await treasuryApi.transfers.list(params)
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
      await treasuryApi.transfers.create(values)
      message.success('调拨申请已提交')
      setModalOpen(false)
      createForm.resetFields()
      fetchData()
    } catch {
      message.error('调拨申请失败')
    }
  }

  const handleApprove = async (id: string) => {
    try {
      await treasuryApi.approve(id, { decision: 'APPROVE' })
      message.success('审批通过')
      fetchData()
    } catch {
      message.error('审批失败')
    }
  }

  const columns = [
    { title: '调拨编号', dataIndex: 'transfer_number', key: 'transfer_number' },
    { title: '转出账户', dataIndex: 'from_account', key: 'from_account' },
    { title: '转入账户', dataIndex: 'to_account', key: 'to_account' },
    { title: '金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'EXECUTED' ? 'green' : v === 'REJECTED' ? 'red' : 'orange'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      record.status === 'PENDING' ? <Button type="link" onClick={() => handleApprove(record.transfer_id)}>审批</Button> : '-'
    )},
  ]

  return (
    <Card title="资金调拨管理" extra={<Button type="primary" onClick={() => setModalOpen(true)}>发起调拨</Button>}>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 150 }} options={TRANSFER_STATUS.map(s => ({ label: s, value: s }))} />
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
      <Table columns={columns} dataSource={data} rowKey="transfer_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="发起资金调拨" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={500}>
        <Form form={createForm} layout="vertical" initialValues={{ currency: 'CNY' }}>
          <Form.Item name="transfer_number" label="调拨编号" rules={[{ required: true }]}>
            <Input placeholder="TRF-2026-001" />
          </Form.Item>
          <Form.Item name="from_account" label="转出账户" rules={[{ required: true }]}>
            <Input placeholder="转出账户号" />
          </Form.Item>
          <Form.Item name="to_account" label="转入账户" rules={[{ required: true }]}>
            <Input placeholder="转入账户号" />
          </Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true }]}>
            <DecimalInput placeholder="0.00" />
          </Form.Item>
          <Form.Item name="currency" label="币种" rules={[{ required: true }]}>
            <Select options={['CNY', 'USD', 'EUR'].map(c => ({ label: c, value: c }))} />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}