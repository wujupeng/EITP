import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { PurchaseReturn } from '@/types/pur'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', submitted: 'blue', approved: 'green',
  shipped: 'orange', completed: 'lime', rejected: 'red',
}

export default function PurReturnManagementPage() {
  const [returns, setReturns] = useState<PurchaseReturn[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.returns.list()
      setReturns(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.returns.create(values)
      message.success('退货单创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'approve' | 'ship') => {
    try {
      if (action === 'submit') await purApi.returns.submit(id)
      else if (action === 'approve') await purApi.returns.approve(id, { approved: true })
      else if (action === 'ship') await purApi.returns.ship(id, { idempotency_key: crypto.randomUUID() })
      message.success('操作成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '退货编码', dataIndex: 'return_code', key: 'return_code' },
    { title: '订单ID', dataIndex: 'order_id', key: 'order_id' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> },
    { title: '操作', key: 'action',
      render: (_: unknown, r: PurchaseReturn) => (
        <Space>
          {r.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(r.return_id, 'submit')}>提交</Button>}
          {r.status === 'submitted' && <Button size="small" type="link" onClick={() => handleAction(r.return_id, 'approve')}>审批</Button>}
          {r.status === 'approved' && <Button size="small" type="link" onClick={() => handleAction(r.return_id, 'ship')}>出库</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建退货单</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={returns} rowKey="return_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建退货单" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="return_code" label="退货编码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="order_id" label="采购订单ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="supplier_id" label="供应商ID" rules={[{ required: true }]}><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}