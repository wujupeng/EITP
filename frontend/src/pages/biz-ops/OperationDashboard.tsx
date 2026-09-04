import { useState, useEffect } from 'react'
import { Table, Card, Tag, Tabs } from 'antd'
import { approvalApi, inventoryStrategyApi } from '@/api/biz-ops'

export default function OperationDashboard() {
  const [pending, setPending] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  const [suggestions, setSuggestions] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [p, a, s] = await Promise.all([
          approvalApi.pending(),
          inventoryStrategyApi.alerts(),
          inventoryStrategyApi.suggestions(),
        ])
        setPending(p.data || [])
        setAlerts(a.data || [])
        setSuggestions(s.data || [])
      } catch {
        // handled by interceptor
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <Card title="业务操作看板">
      <Tabs
        items={[
          {
            key: 'pending',
            label: '待审批',
            children: (
              <Table
                loading={loading}
                dataSource={pending}
                rowKey="approval_id"
                columns={[
                  { title: '审批 ID', dataIndex: 'approval_id' },
                  { title: '流程', dataIndex: 'flow_name' },
                  { title: '节点', dataIndex: 'node_name' },
                  { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color="orange">{v}</Tag> },
                ]}
              />
            ),
          },
          {
            key: 'alerts',
            label: '库存预警',
            children: (
              <Table
                loading={loading}
                dataSource={alerts}
                rowKey="id"
                columns={[
                  { title: 'SKU', dataIndex: 'sku_id' },
                  { title: '仓库', dataIndex: 'warehouse_id' },
                  { title: '预警类型', dataIndex: 'alert_type' },
                  { title: '当前库存', dataIndex: 'current_stock' },
                ]}
              />
            ),
          },
          {
            key: 'suggestions',
            label: '补货建议',
            children: (
              <Table
                loading={loading}
                dataSource={suggestions}
                rowKey="id"
                columns={[
                  { title: 'SKU', dataIndex: 'sku_id' },
                  { title: '建议数量', dataIndex: 'suggested_qty' },
                  { title: '原因', dataIndex: 'reason' },
                ]}
              />
            ),
          },
        ]}
      />
    </Card>
  )
}