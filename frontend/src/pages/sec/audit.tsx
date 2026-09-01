import { useState, useEffect } from 'react'
import { Card, Table, Tag } from 'antd'
import { secApi } from '@/api/sec'

export default function SecAuditPage() {
  const [records, setRecords] = useState<any[]>([])

  useEffect(() => {
    secApi.listAudit().then(resp => setRecords(resp.data.records || []))
  }, [])

  return (
    <Card title="认证审计记录">
      <Table dataSource={records} rowKey="audit_id" columns={[
        { title: '审计ID', dataIndex: 'audit_id' },
        { title: '批次', dataIndex: 'batch_id' },
        { title: '动作', dataIndex: 'action_type', render: (v: string) => <Tag>{v}</Tag> },
        { title: '操作人', dataIndex: 'operator' },
        { title: '时间', dataIndex: 'action_time' },
      ]} />
    </Card>
  )
}