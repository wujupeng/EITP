import { useState, useEffect } from 'react'
import { Table, Button, Input, message, Space, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { ReconcileDiff } from '@/types/pur'

export default function PurReconcileManagementPage() {
  const [diffs, setDiffs] = useState<ReconcileDiff[]>([])
  const [loading, setLoading] = useState(false)
  const [orderId, setOrderId] = useState('')

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.reconcile.listDiffs()
      setDiffs(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleRun = async () => {
    if (!orderId) { message.warning('请输入订单ID'); return }
    try {
      await purApi.reconcile.run(orderId)
      message.success('对账执行成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleRepair = async (diffId: string) => {
    try {
      await purApi.reconcile.repair(diffId)
      message.success('修复成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '订单ID', dataIndex: 'order_id', key: 'order_id' },
    { title: 'SKU', dataIndex: 'sku_id', key: 'sku_id' },
    { title: '采购量', dataIndex: 'pur_quantity', key: 'pur_quantity' },
    { title: 'WMS量', dataIndex: 'wms_quantity', key: 'wms_quantity' },
    { title: 'INV量', dataIndex: 'inv_quantity', key: 'inv_quantity' },
    { title: '差异类型', dataIndex: 'diff_type', key: 'diff_type' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'open' ? 'red' : 'green'}>{s}</Tag> },
    { title: '操作', key: 'action',
      render: (_: unknown, r: ReconcileDiff) => (
        r.status === 'open' ? <Button size="small" type="link" onClick={() => handleRepair(r.diff_id)}>修复</Button> : null
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input placeholder="输入订单ID触发对账" value={orderId} onChange={e => setOrderId(e.target.value)} style={{ width: 300 }} />
        <Button type="primary" onClick={handleRun}>执行对账</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={diffs} rowKey="diff_id" loading={loading} pagination={{ pageSize: 20 }} />
    </div>
  )
}