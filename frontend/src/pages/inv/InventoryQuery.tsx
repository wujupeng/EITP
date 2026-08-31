import { useState, useEffect } from 'react'
import { Table, Card, Tag, Row, Col, Statistic } from 'antd'
import { inventoryApi, type InventoryBalance } from '@/api/inventory'

export default function InventoryQuery() {
  const [balances, setBalances] = useState<InventoryBalance[]>([])
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await inventoryApi.queryBalance()
      setBalances(data)
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const totalOnHand = balances.reduce((sum, b) => sum + b.on_hand, 0)
  const totalReserved = balances.reduce((sum, b) => sum + b.reserved, 0)
  const totalAvailable = balances.reduce((sum, b) => sum + b.available, 0)

  const columns = [
    { title: 'SKU ID', dataIndex: 'sku_id', key: 'sku_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '仓库 ID', dataIndex: 'warehouse_id', key: 'warehouse_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '现有量', dataIndex: 'on_hand', key: 'on_hand' },
    { title: '预留量', dataIndex: 'reserved', key: 'reserved' },
    {
      title: '可用量',
      dataIndex: 'available',
      key: 'available',
      render: (v: number) => <Tag color={v > 0 ? 'green' : 'red'}>{v}</Tag>,
    },
    { title: '在途量', dataIndex: 'in_transit', key: 'in_transit' },
    { title: '待检量', dataIndex: 'inspection', key: 'inspection' },
    { title: '冻结量', dataIndex: 'blocked', key: 'blocked' },
    { title: '单位成本', dataIndex: 'unit_cost', key: 'unit_cost', render: (v: number) => v.toFixed(2) },
  ]

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card><Statistic title="总现有量" value={totalOnHand} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="总预留量" value={totalReserved} /></Card>
        </Col>
        <Col span={8}>
          <Card><Statistic title="总可用量" value={totalAvailable} valueStyle={{ color: totalAvailable > 0 ? '#3f8600' : '#cf1322' }} /></Card>
        </Col>
      </Row>
      <Table
        columns={columns}
        dataSource={balances}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
    </div>
  )
}