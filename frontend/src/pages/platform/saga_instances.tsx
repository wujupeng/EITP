import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button } from 'antd'
import { pltApi } from '@/api/platform'

export default function SagaInstancesPage() {
  const [instances, setInstances] = useState<any[]>([])

  useEffect(() => {
    pltApi.consistency.sagaInstances().then(resp => setInstances(resp.data.items || []))
  }, [])

  return (
    <Card title="Saga 实例管理">
      <Table dataSource={instances} rowKey="saga_id" columns={[
        { title: 'Saga ID', dataIndex: 'saga_id', width: 120 },
        { title: '类型', dataIndex: 'saga_type' },
        { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'RUNNING' ? 'blue' : v === 'COMPLETED' ? 'green' : v === 'COMPENSATING' ? 'orange' : 'red'}>{v}</Tag> },
        { title: '当前步骤', dataIndex: 'current_step' },
        { title: 'TraceID', dataIndex: 'trace_id' },
        { title: '操作', render: (_, record: any) => <Button size="small" onClick={() => pltApi.consistency.compensateSaga(record.saga_id)}>补偿</Button> },
      ]} />
    </Card>
  )
}