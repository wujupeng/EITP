import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { SalesInvoice } from '@/types/sal'

export default function SalInvoiceManagementPage() {
  const [invoices, setInvoices] = useState<SalesInvoice[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [matchOpen, setMatchOpen] = useState(false)
  const [currentId, setCurrentId] = useState('')
  const [form] = Form.useForm()
  const [matchForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.invoices.list()
      setInvoices(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.invoices.create(values)
      message.success('销售发票创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleMatch = async () => {
    const values = await matchForm.validateFields()
    try {
      await salApi.invoices.match(currentId, values)
      message.success('发票匹配成功'); setMatchOpen(false); matchForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '发票编码', dataIndex: 'invoice_code', key: 'invoice_code' },
    { title: '客户ID', dataIndex: 'customer_id', key: 'customer_id' },
    { title: '发票金额', dataIndex: 'invoice_amount', key: 'invoice_amount' },
    { title: '税额', dataIndex: 'tax_amount', key: 'tax_amount' },
    { title: '已匹配', dataIndex: 'matched_amount', key: 'matched_amount' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'matched' ? 'green' : 'default'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: SalesInvoice) => (
        <Space>
          {r.status === 'draft' && (
            <Button size="small" type="link" onClick={() => { setCurrentId(r.invoice_id); setMatchOpen(true) }}>匹配结算单</Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建销售发票</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={invoices} rowKey="invoice_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建销售发票" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="invoice_code" label="发票编码" rules={[{ required: true }]}><Input placeholder="如 INV001" /></Form.Item>
          <Form.Item name="customer_id" label="客户ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="settlement_id" label="结算单ID"><Input /></Form.Item>
          <Form.Item name="invoice_amount" label="发票金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
          <Form.Item name="tax_amount" label="税额"><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
      <Modal title="匹配结算单" open={matchOpen} onOk={handleMatch} onCancel={() => setMatchOpen(false)}>
        <Form form={matchForm} layout="vertical">
          <Form.Item name="settlement_id" label="结算单ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="matched_amount" label="匹配金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}