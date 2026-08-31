import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { Invoice } from '@/types/pur'

export default function PurInvoiceManagementPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.invoices.list()
      setInvoices(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.invoices.create(values)
      message.success('发票创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '发票编码', dataIndex: 'invoice_code', key: 'invoice_code' },
    { title: '供应商', dataIndex: 'supplier_id', key: 'supplier_id' },
    { title: '发票金额', dataIndex: 'invoice_amount', key: 'invoice_amount' },
    { title: '已匹配', dataIndex: 'matched_amount', key: 'matched_amount' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'matched' ? 'green' : 'default'}>{s}</Tag> },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建发票</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={invoices} rowKey="invoice_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建发票" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="invoice_code" label="发票编码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="supplier_id" label="供应商ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="invoice_amount" label="发票金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}