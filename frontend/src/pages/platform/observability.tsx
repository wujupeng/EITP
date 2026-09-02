import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag } from 'antd'
import { pltApi } from '@/api/platform'

export default function ObservabilityPage() {
  const [health, setHealth] = useState<any>({})

  useEffect(() => { pltApi.observability.health().then(resp => setHealth(resp.data)) }, [])

  return (
    <Card title="可观测性">
      <Descriptions bordered column={2}>
        <Descriptions.Item label="健康状态">
          <Tag color={health.status === 'healthy' ? 'green' : 'red'}>{health.status || 'unknown'}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="检查项">{JSON.stringify(health.checks || {})}</Descriptions.Item>
      </Descriptions>
    </Card>
  )
}