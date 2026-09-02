import { useState, useEffect } from 'react'
import { Card, Row, Col, Statistic } from 'antd'
import { pltApi } from '@/api/platform'

export default function PlatformDashboardPage() {
  const [data, setData] = useState<any>({})

  useEffect(() => {
    pltApi.observability.dashboard().then(resp => setData(resp.data))
  }, [])

  return (
    <Card title="平台总览仪表盘">
      <Row gutter={16}>
        <Col span={4}><Statistic title="QPS" value={data.qps || 0} /></Col>
        <Col span={4}><Statistic title="P95 (ms)" value={data.p95 || 0} /></Col>
        <Col span={4}><Statistic title="P99 (ms)" value={data.p99 || 0} /></Col>
        <Col span={4}><Statistic title="错误率" value={data.error_rate || 0} suffix="%" /></Col>
        <Col span={4}><Statistic title="活跃租户" value={data.active_tenants || 0} /></Col>
        <Col span={4}><Statistic title="Outbox待投递" value={data.outbox_pending || 0} /></Col>
      </Row>
    </Card>
  )
}