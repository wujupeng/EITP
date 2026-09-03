import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Table, Button, Statistic, Row, Col } from 'antd'
import { reconciliationApi } from '@/api/fin/reconciliation'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function ReconciliationReportPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [report, setReport] = useState<any>(null)

  useEffect(() => {
    if (id) reconciliationApi.report(id).then(resp => setReport(resp.data))
  }, [id])

  if (!report) return <Card title="对账报告">加载中...</Card>

  const columns = [
    { title: '项目', dataIndex: 'item', key: 'item' },
    { title: '本方金额', dataIndex: 'local_amount', key: 'local_amount', render: (v: string) => formatMoney(v, report.currency) },
    { title: '对方金额', dataIndex: 'remote_amount', key: 'remote_amount', render: (v: string) => formatMoney(v, report.currency) },
    { title: '差异', dataIndex: 'diff_amount', key: 'diff_amount', render: (v: string) => <Tag color="red">{formatMoney(v, report.currency)}</Tag> },
  ]

  return (
    <Card title={`对账报告 - ${report.batch_number}`} extra={<Button onClick={() => navigate('/fin/reconciliations')}>返回</Button>}>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Statistic title="总笔数" value={report.total_count} /></Col>
        <Col span={6}><Statistic title="匹配笔数" value={report.matched_count} valueStyle={{ color: '#52c41a' }} /></Col>
        <Col span={6}><Statistic title="差异笔数" value={report.diff_count} valueStyle={{ color: '#ff4d4f' }} /></Col>
        <Col span={6}><Statistic title="差异金额" value={formatMoney(report.diff_total, report.currency)} /></Col>
      </Row>
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="批次号">{report.batch_number}</Descriptions.Item>
        <Descriptions.Item label="对账类型">{report.recon_type}</Descriptions.Item>
        <Descriptions.Item label="开始时间">{report.started_at}</Descriptions.Item>
        <Descriptions.Item label="结束时间">{report.finished_at || '-'}</Descriptions.Item>
      </Descriptions>
      <Table columns={columns} dataSource={report.details || []} rowKey="item" pagination={false} />
    </Card>
  )
}