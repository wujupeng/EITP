import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { salApi } from '@/api/sal'
import type { SalesOrder, SalesOrderStatus } from '@/types/sal'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', submitted: 'blue', approved: 'cyan', rejected: 'red',
  reserved: 'geekblue', partial_shipped: 'orange', shipped: 'green',
  completed: 'lime', cancelled: 'volcano', closed: 'gray',
}

const STATUS_OPTIONS: { value: SalesOrderStatus; label: string }[] = [
  { value: 'draft', label: '草稿' },
  { value: 'submitted', label: '已提交' },
  { value: 'approved', label: '已审批' },
  { value: 'reserved', label: '已预留' },
  { value: 'partial_shipped', label: '部分发货' },
  { value: 'shipped', label: '已发货' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
  { value: 'closed', label: '已关闭' },
]

export default function SalOrderManagementPage() {
  const [orders, setOrders] = useState<SalesOrder[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [filterStatus, setFilterStatus] = useState<SalesOrderStatus | undefined>(undefined)
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.orders.list({ status: filterStatus })
      setOrders(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => {
    loadData()
    const timer = setInterval(loadData, 10000)
    return () => clearInterval(timer)
  }, [filterStatus])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.orders.create(values)
      message.success('销售订单创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'approve' | 'confirm' | 'cancel' | 'close') => {
    try {
      if (action === 'submit') await salApi.orders.submit(id)
      else if (action === 'approve') await salApi.orders.approve(id, { approved: true })
      else if (action === 'confirm') await salApi.orders.confirm(id, { idempotency_key: crypto.randomUUID() })
      else if (action === 'cancel') await salApi.orders.cancel(id)
      else if (action === 'close') await salApi.orders.close(id)
      message.success('操作成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '订单编码', dataIndex: 'order_code', key: 'order_code' },
    { title: '客户ID', dataIndex: 'customer_id', key: 'customer_id' },
    { title: '总金额', dataIndex: 'total_amount', key: 'total_amount' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: SalesOrder) => (
        <Space>
          <Button size="small" onClick={() => navigate(`/sal/orders/${r.order_id}`)}>详情</Button>
          {r.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(r.order_id, 'submit')}>提交</Button>}
          {r.status === 'submitted' && <Button size="small" type="link" onClick={() => handleAction(r.order_id, 'approve')}>审批</Button>}
          {r.status === 'approved' && <Button size="small" type="link" onClick={() => handleAction(r.order_id, 'confirm')}>确认履约</Button>}
          {['draft', 'submitted', 'approved'].includes(r.status) && <Button size="small" type="link" danger onClick={() => handleAction(r.order_id, 'cancel')}>取消</Button>}
          {r.status === 'completed' && <Button size="small" type="link" onClick={() => handleAction(r.order_id, 'close')}>关闭</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建销售订单</Button>
        <Select
          allowClear
          placeholder="按状态过滤"
          style={{ width: 160 }}
          options={STATUS_OPTIONS}
          value={filterStatus}
          onChange={(v) => setFilterStatus(v)}
        />
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={orders} rowKey="order_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建销售订单" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="order_code" label="订单编码" rules={[{ required: true }]}><Input placeholder="如 SO001" /></Form.Item>
          <Form.Item name="customer_id" label="客户ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="shipping_warehouse_id" label="发货仓库ID"><Input /></Form.Item>
          <Form.Item name="payment_terms" label="付款条款"><Input /></Form.Item>
          <Form.Item name="currency" label="币种" initialValue="CNY"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}