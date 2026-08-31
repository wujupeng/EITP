import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { purApi } from '@/api/pur'
import type { PurchaseOrder } from '@/types/pur'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', submitted: 'blue', approved: 'cyan', sent: 'green',
  receiving: 'orange', completed: 'lime', cancelled: 'red', closed: 'gray',
}

export default function PurOrderManagementPage() {
  const [orders, setOrders] = useState<PurchaseOrder[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.orders.list()
      setOrders(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.orders.create(values)
      message.success('采购订单创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'approve' | 'send' | 'cancel' | 'close') => {
    try {
      if (action === 'submit') await purApi.orders.submit(id)
      else if (action === 'approve') await purApi.orders.approve(id, { approved: true })
      else if (action === 'send') await purApi.orders.send(id)
      else if (action === 'cancel') await purApi.orders.cancel(id)
      else if (action === 'close') await purApi.orders.close(id)
      message.success('操作成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '订单编码', dataIndex: 'order_code', key: 'order_code' },
    { title: '供应商', dataIndex: 'supplier_id', key: 'supplier_id' },
    { title: '总金额', dataIndex: 'total_amount', key: 'total_amount' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> },
    { title: '操作', key: 'action',
      render: (_: unknown, r: PurchaseOrder) => (
        <Space>
          <Button size="small" onClick={() => navigate(`/pur/orders/${r.order_id}`)}>详情</Button>
          {r.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(r.order_id, 'submit')}>提交</Button>}
          {r.status === 'submitted' && <Button size="small" type="link" onClick={() => handleAction(r.order_id, 'approve')}>审批</Button>}
          {r.status === 'approved' && <Button size="small" type="link" onClick={() => handleAction(r.order_id, 'send')}>发送</Button>}
          {['draft', 'submitted', 'approved'].includes(r.status) && <Button size="small" type="link" danger onClick={() => handleAction(r.order_id, 'cancel')}>取消</Button>}
          {r.status === 'completed' && <Button size="small" type="link" onClick={() => handleAction(r.order_id, 'close')}>关闭</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建采购订单</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={orders} rowKey="order_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建采购订单" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="order_code" label="订单编码" rules={[{ required: true }]}><Input placeholder="如 PO001" /></Form.Item>
          <Form.Item name="supplier_id" label="供应商ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="warehouse_id" label="仓库ID"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}