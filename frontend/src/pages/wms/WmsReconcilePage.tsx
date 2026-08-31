import { useState, useEffect } from 'react'
import { Card, Table, Button, Input, Space, Tag, message, Modal, Form, Drawer, Descriptions, Statistic, Row, Col } from 'antd'
import { ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { wmsApi } from '@/api/wms'
import type { ReconcileDiff } from '@/types/wms'

const diffTypeColorMap: Record<string, string> = {
  wms_more: 'orange', inv_more: 'red', status_mismatch: 'purple',
}

export default function WmsReconcilePage() {
  const [diffs, setDiffs] = useState<ReconcileDiff[]>([])
  const [loading, setLoading] = useState(false)
  const [warehouseId, setWarehouseId] = useState('')
  const [running, setRunning] = useState(false)
  const [resolveOpen, setResolveOpen] = useState(false)
  const [currentDiff, setCurrentDiff] = useState<ReconcileDiff | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailDiff, setDetailDiff] = useState<ReconcileDiff | null>(null)
  const [form] = Form.useForm()

  const loadDiffs = async () => {
    setLoading(true)
    try {
      const data = await wmsApi.reconcile.getDiffs()
      setDiffs(data)
    } catch {
      message.error('加载差异列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDiffs()
  }, [])

  const handleRun = async () => {
    if (!warehouseId) {
      message.warning('请输入仓库 ID')
      return
    }
    setRunning(true)
    try {
      const result = await wmsApi.reconcile.run(warehouseId)
      message.success(`对账完成，发现 ${result.length} 个差异`)
      loadDiffs()
    } catch {
      message.error('对账执行失败')
    } finally {
      setRunning(false)
    }
  }

  const handleResolve = async () => {
    if (!currentDiff) return
    const values = await form.validateFields()
    setRunning(true)
    try {
      await wmsApi.reconcile.resolve(currentDiff.diff_id, { resolution_note: values.resolution_note })
      message.success('差异已修复')
      setResolveOpen(false)
      form.resetFields()
      loadDiffs()
    } catch {
      message.error('修复失败')
    } finally {
      setRunning(false)
    }
  }

  const columns = [
    { title: '差异 ID', dataIndex: 'diff_id', key: 'diff_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: 'SKU', dataIndex: 'sku_id', key: 'sku_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '仓库', dataIndex: 'warehouse_id', key: 'warehouse_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: 'WMS 数量', dataIndex: 'wms_quantity', key: 'wms_quantity', render: (v: number) => <Tag color="blue">{v}</Tag> },
    { title: 'INV 数量', dataIndex: 'inv_quantity', key: 'inv_quantity', render: (v: number) => <Tag color="cyan">{v}</Tag> },
    { title: '差异', dataIndex: 'diff_quantity', key: 'diff_quantity', render: (v: number) => <Tag color={v === 0 ? 'green' : 'red'}>{v}</Tag> },
    { title: '类型', dataIndex: 'diff_type', key: 'diff_type', render: (v: string) => <Tag color={diffTypeColorMap[v] || 'default'}>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'open' ? 'orange' : 'green'}>{v}</Tag> },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: ReconcileDiff) => (
        <Space size="small">
          <Button size="small" onClick={() => { setDetailDiff(record); setDetailOpen(true) }}>详情</Button>
          {record.status === 'open' && (
            <Button size="small" type="primary" onClick={() => { setCurrentDiff(record); setResolveOpen(true) }}>修复</Button>
          )}
        </Space>
      ),
    },
  ]

  const openDiffs = diffs.filter((d) => d.status === 'open')
  const totalDiffQty = diffs.reduce((sum, d) => sum + Math.abs(d.diff_quantity), 0)

  return (
    <Card title="对账管理">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}><Card><Statistic title="总差异数" value={diffs.length} /></Card></Col>
        <Col span={8}><Card><Statistic title="未修复差异" value={openDiffs.length} valueStyle={{ color: openDiffs.length > 0 ? '#cf1322' : '#3f8600' }} /></Card></Col>
        <Col span={8}><Card><Statistic title="总差异量" value={totalDiffQty} /></Card></Col>
      </Row>

      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="输入仓库 ID"
          style={{ width: 300 }}
          value={warehouseId}
          onChange={(e) => setWarehouseId(e.target.value)}
        />
        <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleRun} loading={running}>触发对账</Button>
        <Button icon={<ReloadOutlined />} onClick={loadDiffs}>刷新差异</Button>
      </Space>

      <Table columns={columns} dataSource={diffs} rowKey="diff_id" loading={loading} pagination={{ pageSize: 20 }} />

      <Modal title="修复差异" open={resolveOpen} onOk={handleResolve} onCancel={() => setResolveOpen(false)} confirmLoading={running}>
        <Form form={form} layout="vertical">
          {currentDiff && (
            <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="SKU">{currentDiff.sku_id.substring(0, 8)}...</Descriptions.Item>
              <Descriptions.Item label="差异量">{currentDiff.diff_quantity}</Descriptions.Item>
              <Descriptions.Item label="类型">{currentDiff.diff_type}</Descriptions.Item>
            </Descriptions>
          )}
          <Form.Item name="resolution_note" label="修复说明">
            <Input.TextArea placeholder="输入修复说明（可选）" rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="差异详情" open={detailOpen} onClose={() => setDetailOpen(false)} width={400}>
        {detailDiff && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="差异 ID">{detailDiff.diff_id}</Descriptions.Item>
            <Descriptions.Item label="SKU">{detailDiff.sku_id}</Descriptions.Item>
            <Descriptions.Item label="仓库">{detailDiff.warehouse_id}</Descriptions.Item>
            <Descriptions.Item label="WMS 数量">{detailDiff.wms_quantity}</Descriptions.Item>
            <Descriptions.Item label="INV 数量">{detailDiff.inv_quantity}</Descriptions.Item>
            <Descriptions.Item label="差异量">{detailDiff.diff_quantity}</Descriptions.Item>
            <Descriptions.Item label="差异类型"><Tag color={diffTypeColorMap[detailDiff.diff_type]}>{detailDiff.diff_type}</Tag></Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={detailDiff.status === 'open' ? 'orange' : 'green'}>{detailDiff.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="创建时间">{detailDiff.created_at}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </Card>
  )
}
