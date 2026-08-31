import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { PurchaseSettlement } from '@/types/pur'

const STATUS_COLORS: Record<string, string> = {
  pending: 'default', reconciled: 'blue', diff_found: 'red',
  invoice_matched: 'cyan', payment_requested: 'orange', completed: 'green',
}

export default function PurSettlementManagementPage() {
  const [settlements, setSettlements] = useState<PurchaseSettlement[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [reconcileOpen, setReconcileOpen] = useState(false)
  const [currentId, setCurrentId] = useState('')
  const [form] = Form.useForm()
  const [reconcileForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.settlements.list()
      setSettlements(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.settlements.create(values)
      message.success('结算单创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleReconcile = async () => {
    const values = await reconcileForm.validateFields()
    try {
      await purApi.settlements.reconcile(currentId, values)
      message.success('对账成功')
      setReconcileOpen(false); reconcileForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '结算编码', dataIndex: 'settlement_code', key: 'settlement_code' },
    { title: '订单ID', dataIndex: 'order_id', key: 'order_id' },
    { title: '总金额', dataIndex: 'total_amount', key: 'total_amount' },
    { title: '差异', dataIndex: 'diff_amount', key: 'diff_amount' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> },
    { title: '操作', key: 'action',
      render: (_: unknown, r: PurchaseSettlement) => (
        <Space>
          {r.status === 'pending' && (
            <Button size="small" type="primary" onClick={() => { setCurrentId(r.settlement_id); setReconcileOpen(true) }}>对账</Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建结算单</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={settlements} rowKey="settlement_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建结算单" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="settlement_code" label="结算编码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="order_id" label="订单ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="supplier_id" label="供应商ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="total_amount" label="总金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
      <Modal title="对账确认" open={reconcileOpen} onOk={handleReconcile} onCancel={() => setReconcileOpen(false)}>
        <Form form={reconcileForm} layout="vertical">
          <Form.Item name="received_amount" label="实际收货金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}