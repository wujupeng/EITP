import { useState, useEffect } from 'react'
import { Table, Button, Input, message, Space, Tag, Card, Descriptions } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { ReconcileDiff } from '@/types/sal'

export default function SalReconcileManagementPage() {
  const [diffs, setDiffs] = useState<ReconcileDiff[]>([])
  const [loading, setLoading] = useState(false)
  const [orderId, setOrderId] = useState('')
  const [lastResult, setLastResult] = useState<Record<string, unknown> | null>(null)

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.reconcile.listDiffs()
      setDiffs(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleRun = async () => {
    if (!orderId) { message.warning('请输入订单ID'); return }
    try {
      const result = await salApi.reconcile.run(orderId)
      message.success('三边对账执行成功')
      setLastResult(result); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleRepair = async (diffId: string) => {
    try {
      await salApi.reconcile.repair(diffId)
      message.success('修复成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '订单ID', dataIndex: 'order_id', key: 'order_id' },
    { title: 'SKU', dataIndex: 'sku_id', key: 'sku_id' },
    { title: '仓库', dataIndex: 'warehouse_id', key: 'warehouse_id' },
    { title: '销售量', dataIndex: 'sal_quantity', key: 'sal_quantity' },
    { title: 'WMS量', dataIndex: 'wms_quantity', key: 'wms_quantity' },
    { title: 'INV量', dataIndex: 'inv_quantity', key: 'inv_quantity' },
    { title: '差异类型', dataIndex: 'diff_type', key: 'diff_type' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'open' ? 'red' : 'green'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: ReconcileDiff) => (
        r.status === 'open' ? <Button size="small" type="link" onClick={() => handleRepair(r.diff_id)}>修复</Button> : null
      ),
    },
  ]

  const openDiffs = diffs.filter((d) => d.status === 'open').length
  const consistent = openDiffs === 0

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input placeholder="输入订单ID触发三边对账" value={orderId} onChange={(e) => setOrderId(e.target.value)} style={{ width: 300 }} />
        <Button type="primary" onClick={handleRun}>执行对账</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Card style={{ marginBottom: 16 }}>
        <Descriptions title="三边对账总览" column={3} size="small">
          <Descriptions.Item label="差异总数">{diffs.length}</Descriptions.Item>
          <Descriptions.Item label="未修复">{openDiffs}</Descriptions.Item>
          <Descriptions.Item label="三边一致">
            <Tag color={consistent ? 'green' : 'red'}>{consistent ? '一致' : '存在差异'}</Tag>
          </Descriptions.Item>
        </Descriptions>
      </Card>
      {lastResult && (
        <Card title="最近对账结果" style={{ marginBottom: 16 }} size="small">
          <pre style={{ margin: 0 }}>{JSON.stringify(lastResult, null, 2)}</pre>
        </Card>
      )}
      <Table columns={columns} dataSource={diffs} rowKey="diff_id" loading={loading} pagination={{ pageSize: 20 }} />
    </div>
  )
}