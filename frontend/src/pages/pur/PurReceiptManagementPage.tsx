import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, message, Space, Tag, Drawer } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { PurchaseReceipt } from '@/types/pur'

const STATUS_COLORS: Record<string, string> = {
  pending: 'default', confirmed: 'green', failed: 'red',
}

export default function PurReceiptManagementPage() {
  const [receipts, setReceipts] = useState<PurchaseReceipt[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [currentId, setCurrentId] = useState('')
  const [form] = Form.useForm()
  const [confirmForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.receipts.list()
      setReceipts(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.receipts.create(values)
      message.success('收货单创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleConfirm = async () => {
    const values = await confirmForm.validateFields()
    try {
      const idempotencyKey = crypto.randomUUID()
      await purApi.receipts.confirm(currentId, { ...values, idempotency_key: idempotencyKey })
      message.success('收货确认成功（已通过WMS Receiving API触发收货）')
      setConfirmOpen(false); confirmForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '收货单编码', dataIndex: 'receipt_code', key: 'receipt_code' },
    { title: '订单ID', dataIndex: 'order_id', key: 'order_id' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> },
    { title: 'WMS收货ID', dataIndex: 'wms_receiving_id', key: 'wms_receiving_id' },
    { title: '操作', key: 'action',
      render: (_: unknown, r: PurchaseReceipt) => (
        <Space>
          {r.status === 'pending' && <Button size="small" type="primary" onClick={() => { setCurrentId(r.receipt_id); setConfirmOpen(true) }}>收货确认</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建收货单</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={receipts} rowKey="receipt_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建收货单" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="receipt_code" label="收货单编码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="order_id" label="采购订单ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="supplier_id" label="供应商ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="warehouse_id" label="仓库ID" rules={[{ required: true }]}><Input /></Form.Item>
        </Form>
      </Modal>
      <Drawer title="收货确认（通过WMS Receiving API）" open={confirmOpen} onClose={() => setConfirmOpen(false)} width={500}
        footer={<Space><Button onClick={() => setConfirmOpen(false)}>取消</Button><Button type="primary" onClick={handleConfirm}>确认收货</Button></Space>}
      >
        <Form form={confirmForm} layout="vertical">
          <Form.Item name="receiving_zone_id" label="收货库区ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="location_id" label="库位ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="received_quantity" label="收货数量" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}