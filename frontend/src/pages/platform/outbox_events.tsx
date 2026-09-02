import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button } from 'antd'
import { pltApi } from '@/api/platform'

export default function OutboxEventsPage() {
  const [events, setEvents] = useState<any[]>([])

  useEffect(() => {
    pltApi.consistency.outboxEvents({ status: 'PENDING' }).then(resp => setEvents(resp.data.items || []))
  }, [])

  return (
    <Card title="Outbox 事件管理">
      <Table dataSource={events} rowKey="event_id" columns={[
        { title: '事件ID', dataIndex: 'event_id', width: 120 },
        { title: '类型', dataIndex: 'event_type' },
        { title: '聚合根', dataIndex: 'aggregate_root_type' },
        { title: '状态', dataIndex: 'delivery_status', render: (v: string) => <Tag color={v === 'PENDING' ? 'orange' : v === 'DELIVERED' ? 'green' : 'red'}>{v}</Tag> },
        { title: '尝试次数', dataIndex: 'delivery_attempts' },
        { title: '创建时间', dataIndex: 'created_at' },
        { title: '操作', render: (_, record: any) => <Button size="small" onClick={() => pltApi.consistency.retryOutbox(record.event_id)}>重投</Button> },
      ]} />
    </Card>
  )
}