import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Descriptions, Tabs, Timeline, Tag, Spin, Table, Progress, Space, Button, message } from 'antd'
import { salApi } from '@/api/sal'
import type { SalesOrderLine } from '@/types/sal'

function SalesOrderLineFourState({ line }: { line: SalesOrderLine }) {
  const ordered = line.ordered_quantity
  const reserved = line.reserved_quantity
  const shipped = line.shipped_quantity
  const remaining = line.remaining_quantity
  const shippedPercent = ordered > 0 ? Math.round((shipped / ordered) * 100) : 0
  const reservedPercent = ordered > 0 ? Math.round((reserved / ordered) * 100) : 0
  const invariantOk = remaining === ordered - shipped && shipped <= ordered && reserved >= shipped && reserved <= ordered

  return (
    <div style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
      <Space style={{ marginBottom: 4 }}>
        <Tag color="blue">SKU: {line.enterprise_sku_id}</Tag>
        <Tag color="default">行状态: {line.line_status}</Tag>
        <Tag color={invariantOk ? 'green' : 'red'}>{invariantOk ? '四态守恒' : '守恒破坏'}</Tag>
      </Space>
      <div style={{ display: 'flex', gap: 16, marginBottom: 4 }}>
        <span>订购: <strong>{ordered}</strong></span>
        <span>已预留: <strong style={{ color: '#1677ff' }}>{reserved}</strong></span>
        <span>已发货: <strong style={{ color: '#52c41a' }}>{shipped}</strong></span>
        <span>剩余: <strong style={{ color: '#fa8c16' }}>{remaining}</strong></span>
        <span>单价: {line.unit_price}</span>
      </div>
      <Progress
        percent={shippedPercent}
        success={{ percent: reservedPercent, strokeColor: '#1677ff' }}
        strokeColor="#52c41a"
        format={(p) => `已发 ${p}% / 已预留 ${reservedPercent}%`}
      />
    </div>
  )
}

export default function SalOrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [order, setOrder] = useState<Record<string, unknown> | null>(null)
  const [lines, setLines] = useState<SalesOrderLine[]>([])
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [orderData, linesData, traceData] = await Promise.all([
        salApi.orders.get(id),
        salApi.orders.getLines(id).catch(() => [] as SalesOrderLine[]),
        salApi.orders.trace(id).catch(() => null),
      ])
      setOrder(orderData as unknown as Record<string, unknown>)
      setLines(linesData)
      setTrace(traceData)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [id])

  const handleConfirm = async () => {
    if (!id) return
    try {
      await salApi.orders.confirm(id, { idempotency_key: crypto.randomUUID() })
      message.success('确认履约成功，已触发 INV Reservation API 预留')
      loadData()
    } catch { /* handled by interceptor */ }
  }

  if (loading) return <Spin />
  if (!order) return <div>订单不存在</div>

  const status = order['status'] as string
  const totalOrdered = lines.reduce((s, l) => s + l.ordered_quantity, 0)
  const totalShipped = lines.reduce((s, l) => s + l.shipped_quantity, 0)
  const totalReserved = lines.reduce((s, l) => s + l.reserved_quantity, 0)
  const totalRemaining = lines.reduce((s, l) => s + l.remaining_quantity, 0)

  return (
    <div>
      <Descriptions title="销售订单详情" bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="订单编码">{order['order_code'] as string}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag>{status}</Tag></Descriptions.Item>
        <Descriptions.Item label="客户">{order['customer_id'] as string}</Descriptions.Item>
        <Descriptions.Item label="发货仓库">{order['shipping_warehouse_id'] as string ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="总金额">{order['total_amount'] as number}</Descriptions.Item>
        <Descriptions.Item label="来源报价">{order['source_quotation_id'] as string ?? '-'}</Descriptions.Item>
      </Descriptions>

      {status === 'approved' && (
        <Button type="primary" onClick={handleConfirm} style={{ marginBottom: 16 }}>
          确认履约（触发 INV 预留）
        </Button>
      )}

      <Tabs
        items={[
          {
            key: 'lines', label: '订单行（四态守恒）',
            children: (
              <div>
                <Space style={{ marginBottom: 8 }}>
                  <Tag color="blue">总订购: {totalOrdered}</Tag>
                  <Tag color="cyan">总预留: {totalReserved}</Tag>
                  <Tag color="green">总已发: {totalShipped}</Tag>
                  <Tag color="orange">总剩余: {totalRemaining}</Tag>
                </Space>
                {lines.length === 0 ? (
                  <div>暂无订单行</div>
                ) : (
                  lines.map((line) => <SalesOrderLineFourState key={line.line_id} line={line} />)
                )}
              </div>
            ),
          },
          {
            key: 'reservations', label: '库存预留',
            children: (
              <div>
                {((order['reservation_ids'] as string[]) || []).length === 0
                  ? <div>暂无预留</div>
                  : <Table
                      columns={[
                        { title: '预留ID', dataIndex: 'id', key: 'id' },
                      ]}
                      dataSource={((order['reservation_ids'] as string[]) || []).map((rid) => ({ id: rid, key: rid }))}
                      pagination={false}
                      size="small"
                    />}
              </div>
            ),
          },
          {
            key: 'trace', label: '执行链路',
            children: trace ? (
              <Timeline
                items={[
                  { children: `总订购量: ${trace['total_ordered']}`, color: 'blue' },
                  { children: `总预留量: ${trace['total_reserved']}`, color: 'cyan' },
                  { children: `总发货量: ${trace['total_shipped']}`, color: 'green' },
                  { children: `状态: ${trace['status']}`, color: 'gray' },
                ]}
              />
            ) : <div>暂无链路数据</div>,
          },
        ]}
      />
    </div>
  )
}