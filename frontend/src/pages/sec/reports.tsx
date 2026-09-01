import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button } from 'antd'
import { secApi } from '@/api/sec'
import { useNavigate } from 'react-router-dom'

export default function SecReportsPage() {
  const [reports, setReports] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    secApi.listReports().then(resp => setReports(resp.data.reports || []))
  }, [])

  return (
    <Card title="认证报告列表">
      <Table dataSource={reports} rowKey="report_id" columns={[
        { title: '报告ID', dataIndex: 'report_id' },
        { title: '矩阵版本', dataIndex: 'matrix_version' },
        { title: '执行时间', dataIndex: 'executed_at' },
        { title: '通过率', dataIndex: 'pass_rate', render: (v: number) => <Tag color={v >= 1 ? 'green' : 'red'}>{(v * 100).toFixed(1)}%</Tag> },
        { title: '操作', render: (_, record) => <Button onClick={() => navigate(`/platform/sec/reports/${record.report_id}`)}>查看详情</Button> },
      ]} />
    </Card>
  )
}