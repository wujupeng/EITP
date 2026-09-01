import { useState, useEffect } from 'react'
import { Card, Descriptions, Table, Tag, Collapse, Space } from 'antd'
import { secApi } from '@/api/sec'
import { useParams } from 'react-router-dom'

export default function SecReportDetailPage() {
  const { id } = useParams()
  const [report, setReport] = useState<any>(null)

  useEffect(() => {
    if (id) secApi.getReport(id).then(resp => setReport(resp.data))
  }, [id])

  if (!report) return <Card>加载中...</Card>

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Card title="报告汇总">
        <Descriptions items={[
          { key: 'report_id', label: '报告ID', children: report.report_id },
          { key: 'matrix_version', label: '矩阵版本', children: report.matrix_version },
          { key: 'total', label: '总认证项', children: report.total_items },
          { key: 'passed', label: '通过', children: <Tag color="green">{report.passed_count}</Tag> },
          { key: 'failed', label: '失败', children: <Tag color="red">{report.failed_count}</Tag> },
          { key: 'unexecutable', label: '无法执行', children: <Tag color="orange">{report.unexecutable_count}</Tag> },
        ]} />
      </Card>
      {report.failed_items && (
        <Card title="失败项明细">
          <Table dataSource={report.failed_items} rowKey="item_id" columns={[
            { title: '认证项', dataIndex: 'item_id' },
            { title: '层级', dataIndex: 'layer' },
            { title: '操作', dataIndex: 'operation' },
            { title: '聚合根', dataIndex: 'aggregate_root' },
            { title: '失败原因', dataIndex: 'failure_reason' },
          ]} />
        </Card>
      )}
    </Space>
  )
}