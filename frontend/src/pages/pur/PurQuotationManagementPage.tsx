import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { Quotation } from '@/types/pur'

export default function PurQuotationManagementPage() {
  const [quotations, setQuotations] = useState<Quotation[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.quotations.list()
      setQuotations(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.quotations.create(values)
      message.success('报价单创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '报价单编码', dataIndex: 'quotation_code', key: 'quotation_code' },
    { title: '供应商ID', dataIndex: 'supplier_id', key: 'supplier_id' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'active' ? 'green' : 'default'}>{s}</Tag>,
    },
    { title: '有效期至', dataIndex: 'valid_until', key: 'valid_until' },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建报价单</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={quotations} rowKey="quotation_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建报价单" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="quotation_code" label="报价单编码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="supplier_id" label="供应商ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="payment_terms" label="付款条款"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}