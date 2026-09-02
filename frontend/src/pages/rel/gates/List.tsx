import { useState, useEffect } from 'react'
import { Card, Table, Tag } from 'antd'
import { relApi } from '@/api/rel'
import { useParams } from 'react-router-dom'

export default function RelGateListPage() {
  const { releaseId } = useParams<{ releaseId: string }>()
  const [gates, setGates] = useState<any[]>([])

  useEffect(() => {
    if (releaseId) relApi.gate.list(releaseId).then(resp => setGates(resp.data?.gates || []))
  }, [releaseId])

  const columns = [
    { title: '门禁类型', dataIndex: 'gate_type', key: 'gate_type' },
    { title: '结果', dataIndex: 'gate_result', key: 'gate_result', render: (v: string) => (
      <Tag color={v === 'PASS' ? 'green' : 'red'}>{v}</Tag>
    )},
    { title: '执行人', dataIndex: 'executed_by', key: 'executed_by' },
    { title: '执行时间', dataIndex: 'gate_time', key: 'gate_time' },
  ]

  return (
    <Card title={`门禁记录 - ${releaseId}`}>
      <Table columns={columns} dataSource={gates} rowKey="gate_id" pagination={false} />
    </Card>
  )
}