import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Alert } from 'antd'
import { relApi } from '@/api/rel'
import { useParams } from 'react-router-dom'

export default function RelDeclarationDetailPage() {
  const { releaseId } = useParams<{ releaseId: string }>()
  const [declaration, setDeclaration] = useState<any>(null)

  useEffect(() => {
    if (releaseId) relApi.declaration.get(releaseId).then(resp => setDeclaration(resp.data))
  }, [releaseId])

  if (!declaration) return <Card title="冻结声明">加载中...</Card>

  return (
    <Card title="Core Freeze 冻结声明">
      <Alert message="此声明为 Release 1.0 永久冻结，不可删除" type="warning" showIcon style={{ marginBottom: 16 }} />
      <Descriptions bordered column={1}>
        <Descriptions.Item label="声明ID">{declaration.declaration_id}</Descriptions.Item>
        <Descriptions.Item label="封版ID">{declaration.release_id}</Descriptions.Item>
        <Descriptions.Item label="冻结范围">{declaration.freeze_scope?.join(', ')}</Descriptions.Item>
        <Descriptions.Item label="冻结基线哈希">{declaration.freeze_baseline_hash}</Descriptions.Item>
        <Descriptions.Item label="声明状态"><Tag color={declaration.declaration_status === 'EFFECTIVE' ? 'green' : 'orange'}>{declaration.declaration_status}</Tag></Descriptions.Item>
        <Descriptions.Item label="冻结时间">{declaration.freeze_time}</Descriptions.Item>
      </Descriptions>
    </Card>
  )
}