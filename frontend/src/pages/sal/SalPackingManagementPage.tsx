import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { PackingRecord } from '@/types/sal'

const STATUS_COLORS: Record<string, string> = {
  pending: 'default', completed: 'green',
}

export default function SalPackingManagementPage() {
  const [packings, setPackings] = useState<PackingRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const shipData = await salApi.shipments.list()
      const allPackings = await Promise.all(
        shipData.map((s) => salApi.packing.listByShipment(s.shipment_id).catch(() => [] as PackingRecord[])),
      )
      setPackings(allPackings.flat())
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.packing.create(values)
      message.success('包装记录创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleComplete = async (id: string) => {
    try {
      await salApi.packing.complete(id)
      message.success('包装完成'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '包装编码', dataIndex: 'packing_code', key: 'packing_code' },
    { title: '发货单ID', dataIndex: 'shipment_id', key: 'shipment_id' },
    { title: '件数', dataIndex: 'package_count', key: 'package_count' },
    { title: '毛重', dataIndex: 'total_gross_weight', key: 'total_gross_weight' },
    { title: '净重', dataIndex: 'total_net_weight', key: 'total_net_weight' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: PackingRecord) => (
        <Space>
          {r.status === 'pending' && <Button size="small" type="primary" onClick={() => handleComplete(r.packing_id)}>完成包装</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建包装记录</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={packings} rowKey="packing_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建包装记录" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="shipment_id" label="发货单" rules={[{ required: true }]}>
            <Input placeholder="发货单ID" />
          </Form.Item>
          <Form.Item name="packing_code" label="包装编码" rules={[{ required: true }]}><Input placeholder="如 PK001" /></Form.Item>
          <Form.Item name="package_count" label="件数" rules={[{ required: true }]}><InputNumber min={1} /></Form.Item>
          <Form.Item name="total_gross_weight" label="总毛重(kg)" rules={[{ required: true }]}><InputNumber min={0} step={0.01} /></Form.Item>
          <Form.Item name="total_net_weight" label="总净重(kg)" rules={[{ required: true }]}><InputNumber min={0} step={0.01} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}