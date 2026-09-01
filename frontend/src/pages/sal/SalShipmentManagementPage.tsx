import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, message, Space, Tag, Drawer } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { PickingStrategy, ShipmentOrder, SalesOrder, SalesOrderLine } from '@/types/sal'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', picking: 'blue', packed: 'cyan',
  shipped: 'green', cancelled: 'red', failed: 'volcano',
}

interface ShipLineForm {
  order_line_id: string
  enterprise_sku_id: string
  ship_quantity: number
}

export default function SalShipmentManagementPage() {
  const [shipments, setShipments] = useState<ShipmentOrder[]>([])
  const [orders, setOrders] = useState<SalesOrder[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [currentId, setCurrentId] = useState('')
  const [orderLines, setOrderLines] = useState<SalesOrderLine[]>([])
  const [form] = Form.useForm()
  const [confirmForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [shipData, orderData] = await Promise.all([
        salApi.shipments.list(),
        salApi.orders.list(),
      ])
      setShipments(shipData)
      setOrders(orderData)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleOrderSelect = async (orderId: string) => {
    try {
      const lines = await salApi.orders.getLines(orderId)
      setOrderLines(lines)
      const initialLines: ShipLineForm[] = lines.map((l) => ({
        order_line_id: l.line_id,
        enterprise_sku_id: l.enterprise_sku_id,
        ship_quantity: l.remaining_quantity,
      }))
      form.setFieldValue('lines', initialLines)
    } catch {
      setOrderLines([])
    }
  }

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.shipments.create(values)
      message.success('发货单创建成功（支持部分发货）')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'cancel') => {
    try {
      if (action === 'submit') await salApi.shipments.submit(id)
      else if (action === 'cancel') await salApi.shipments.cancel(id)
      message.success('操作成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleConfirm = async () => {
    const values = await confirmForm.validateFields()
    try {
      const idempotencyKey = values.idempotency_key || crypto.randomUUID()
      await salApi.shipments.confirm(currentId, {
        logistics_tracking_no: values.logistics_tracking_no,
        idempotency_key: idempotencyKey,
      })
      message.success('发货确认成功（已通过 WMS Shipping API 触发 INV SALES_SHIPMENT 扣减）')
      setConfirmOpen(false); confirmForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '发货编码', dataIndex: 'shipment_code', key: 'shipment_code' },
    { title: '订单ID', dataIndex: 'order_id', key: 'order_id' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    { title: 'WMS拣货', dataIndex: 'wms_picking_id', key: 'wms_picking_id' },
    { title: 'WMS发货', dataIndex: 'wms_shipping_id', key: 'wms_shipping_id' },
    { title: '物流单号', dataIndex: 'logistics_tracking_no', key: 'logistics_tracking_no' },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: ShipmentOrder) => (
        <Space>
          {r.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(r.shipment_id, 'submit')}>提交拣货</Button>}
          {r.status === 'packed' && (
            <Button size="small" type="primary" onClick={() => { setCurrentId(r.shipment_id); confirmForm.resetFields(); setConfirmOpen(true) }}>发货确认</Button>
          )}
          {['draft', 'picking'].includes(r.status) && <Button size="small" type="link" danger onClick={() => handleAction(r.shipment_id, 'cancel')}>取消</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建发货单</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={shipments} rowKey="shipment_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建发货单（支持部分发货）" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={800}>
        <Form form={form} layout="vertical">
          <Form.Item name="shipment_code" label="发货编码" rules={[{ required: true }]}><Input placeholder="如 SH001" /></Form.Item>
          <Form.Item name="order_id" label="销售订单" rules={[{ required: true }]}>
            <Select
              showSearch
              placeholder="选择订单"
              options={orders.map((o) => ({ value: o.order_id, label: `${o.order_code} (${o.status})` }))}
              onChange={handleOrderSelect}
            />
          </Form.Item>
          <Form.Item name="customer_id" label="客户ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="shipping_warehouse_id" label="发货仓库ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="picking_strategy" label="拣货策略" initialValue="fifo">
            <Select options={[
              { value: 'fifo' as PickingStrategy, label: 'FIFO' },
              { value: 'fefo' as PickingStrategy, label: 'FEFO' },
              { value: 'by_location' as PickingStrategy, label: '按库位' },
              { value: 'by_batch' as PickingStrategy, label: '按批次' },
            ]} />
          </Form.Item>
          <Form.List name="lines">
            {(fields) => (
              <div>
                <div style={{ marginBottom: 8, color: '#888' }}>
                  可发货量 = remaining_quantity（部分发货可调整 ship_quantity ≤ remaining）
                </div>
                {fields.map((field) => (
                  <Space key={field.key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                    <Form.Item name={[field.name, 'order_line_id']}><Input placeholder="订单行ID" /></Form.Item>
                    <Form.Item name={[field.name, 'enterprise_sku_id']}><Input placeholder="SKU ID" /></Form.Item>
                    <Form.Item name={[field.name, 'ship_quantity']}><InputNumber min={0} placeholder="发货数量" /></Form.Item>
                  </Space>
                ))}
              </div>
            )}
          </Form.List>
          {orderLines.length > 0 && (
            <div style={{ marginTop: 8, padding: 8, background: '#fafafa' }}>
              <div style={{ marginBottom: 4, fontWeight: 500 }}>订单行四态参考：</div>
              {orderLines.map((l) => (
                <div key={l.line_id}>
                  SKU {l.enterprise_sku_id}: 订购 {l.ordered_quantity} / 已发 {l.shipped_quantity} / 可发 {l.remaining_quantity}
                </div>
              ))}
            </div>
          )}
        </Form>
      </Modal>
      <Drawer
        title="发货确认（通过 WMS Shipping API）"
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        width={500}
        footer={<Space><Button onClick={() => setConfirmOpen(false)}>取消</Button><Button type="primary" onClick={handleConfirm}>确认发货</Button></Space>}
      >
        <Form form={confirmForm} layout="vertical">
          <Form.Item name="logistics_tracking_no" label="物流单号"><Input placeholder="可选" /></Form.Item>
          <Form.Item name="idempotency_key" label="幂等键" extra="防止重复提交，留空自动生成 UUID">
            <Input placeholder="自动生成 UUID" />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}