import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Statistic, Row, Col } from 'antd'
import { relApi } from '@/api/rel'
import { useParams } from 'react-router-dom'

export default function RelReportDetailPage() {
  const { releaseId } = useParams<{ releaseId: string }>()
  const [report, setReport] = useState<any>(null)

  useEffect(() => {
    if (releaseId) relApi.report.get(releaseId).then(resp => setReport(resp.data))
  }, [releaseId])

  if (!report) return <Card title="封版报告">加载中...</Card>

  return (
    <Card title="封版报告">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Statistic title="门禁通过" value={report.all_gates_pass ? '是' : '否'} /></Col>
        <Col span={6}><Statistic title="快照校验" value={report.all_snapshots_verified ? '通过' : '失败'} /></Col>
        <Col span={6}><Statistic title="冻结声明" value={report.declaration_effective ? '生效' : '未生效'} /></Col>
        <Col span={6}><Statistic title="测试总数" value={report.test_total} /></Col>
      </Row>
      <Descriptions bordered column={1}>
        <Descriptions.Item label="封版编号">{report.release_number}</Descriptions.Item>
        <Descriptions.Item label="版本">{report.version}</Descriptions.Item>
        <Descriptions.Item label="Git Tag">{report.git_tag}</Descriptions.Item>
        <Descriptions.Item label="证据哈希">{report.evidence_hash}</Descriptions.Item>
        <Descriptions.Item label="核心冻结哈希">{report.core_freeze_hash}</Descriptions.Item>
        <Descriptions.Item label="裁决"><Tag color={report.verdict === 'FINAL_PASS' ? 'green' : 'red'}>{report.verdict || 'PENDING'}</Tag></Descriptions.Item>
      </Descriptions>
    </Card>
  )
}