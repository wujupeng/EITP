import { useState, useEffect } from 'react'
import { Table, Card, Input, Select, Space } from 'antd'
import { auditApi } from '@/api/biz-ops'

export default function AuditQuery() {
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [operationType, setOperationType] = useState<string | undefined>()

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await auditApi.operations({ operation_type: operationType, page, page_size: 20 })
      setData(res.data.items || [])
      setTotal(res.data.total || 0)
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [page, operationType])

  return (
    <Card title="操作审计查询">
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="操作类型"
          allowClear
          style={{ width: 200 }}
          onChange={(v) => { setOperationType(v); setPage(1) }}
          options={[
            { label: '采购订单创建', value: 'purchase_order_create' },
            { label: '采购收货', value: 'purchase_receipt' },
            { label: '销售订单创建', value: 'sales_order_create' },
            { label: '销售发货', value: 'sales_shipment' },
            { label: '库存入库', value: 'inventory_inbound' },
            { label: '库存出库', value: 'inventory_outbound' },
            { label: '仓库收货', value: 'warehouse_receiving' },
            { label: '仓库拣货', value: 'warehouse_picking' },
          ]}
        />
      </Space>
      <Table
        loading={loading}
        dataSource={data}
        rowKey="id"
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: setPage,
        }}
        columns={[
          { title: 'Trace ID', dataIndex: 'trace_id', width: 200 },
          { title: '操作类型', dataIndex: 'operation_type' },
          { title: '实体类型', dataIndex: 'entity_type' },
          { title: '实体 ID', dataIndex: 'entity_id', width: 200 },
          { title: '操作时间', dataIndex: 'occurred_at', width: 180 },
        ]}
      />
    </Card>
  )
}