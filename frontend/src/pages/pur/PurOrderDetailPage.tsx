import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Descriptions, Tabs, Timeline, Tag, Spin } from 'antd'
import { purApi } from '@/api/pur'

export default function PurOrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [order, setOrder] = useState<Record<string, unknown> | null>(null)
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [orderData, traceData] = await Promise.all([
        purApi.orders.get(id),
        purApi.orders.trace(id).catch(() => null),
      ])
      setOrder(orderData)
      setTrace(traceData)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [id])

  if (loading) return <Spin />
  if (!order) return <div>订单不存在</div>

  const lines = (order['lines'] as Record<string, unknown>[]) || []

  return (
    <div>
      <Descriptions title="采购订单详情" bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="订单编码">{order['order_code'] as string}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag>{order['status'] as string}</Tag></Descriptions.Item>
        <Descriptions.Item label="供应商">{order['supplier_id'] as string}</Descriptions.Item>
        <Descriptions.Item label="总金额">{order['total_amount'] as number}</Descriptions.Item>
      </Descriptions>
      <Tabs
        items={[
          {
            key: 'lines', label: '订单行',
            children: (
              <div>
                {lines.map((line, i) => (
                  <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                    SKU: {line['sku_id'] as string} |
                    订购: {line['ordered_quantity'] as number} |
                    已收: {line['received_quantity'] as number} |
                    单价: {line['unit_price'] as number}
                  </div>
                ))}
              </div>
            ),
          },
          {
            key: 'trace', label: '执行链路',
            children: trace ? (
              <Timeline
                items={[
                  { children: `总订购量: ${trace['total_ordered']}`, color: 'blue' },
                  { children: `总收货量: ${trace['total_received']}`, color: 'green' },
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