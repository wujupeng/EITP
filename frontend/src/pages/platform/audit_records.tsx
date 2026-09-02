import { useState, useEffect } from 'react'
import { Card, Table, Tag, Input, Select, Space } from 'antd'
import { pltApi } from '@/api/platform'

export default function AuditRecordsPage() {
  const [records, setRecords] = useState<any[]>([])
  const [module, setModule] = useState<string>()
  const [traceId, setTraceId] = useState<string>()

  useEffect(() => {
    pltApi.audit.records({ module, trace_id: traceId }).then(resp => setRecords(resp.data.items || []))
  }, [module, traceId])

  return (
    <Card title="统一审计记录查询">
      <Space style={{ marginBottom: 16 }}>
        <Select placeholder="模块" allowClear onChange={v => setModule(v)} options={[
          'MT','IAM','INV','MDM','WMS','PUR','SAL','SEC','PLT'
        ].map(m => ({ label: m, value: m }))} />
        <Input placeholder="Trace ID" allowClear onChange={e => setTraceId(e.target.value)} />
      </Space>
      <Table dataSource={records} rowKey="audit_id" columns={[
        { title: '审计ID', dataIndex: 'audit_id', width: 120 },
        { title: '模块', dataIndex: 'module', render: (v: string) => <Tag>{v}</Tag> },
        { title: '聚合根', dataIndex: 'aggregate_root_type' },
        { title: '操作', dataIndex: 'operation_type' },
        { title: '操作人', dataIndex: 'operator_id' },
        { title: 'TraceID', dataIndex: 'trace_id' },
        { title: '时间', dataIndex: 'timestamp' },
      ]} />
    </Card>
  )
}