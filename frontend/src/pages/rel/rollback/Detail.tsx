import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Button } from 'antd'
import { relApi } from '@/api/rel'
import { useParams, useNavigate } from 'react-router-dom'

export default function RelRollbackDetailPage() {
  const { releaseId } = useParams<{ releaseId: string }>()
  const navigate = useNavigate()
  const [plan, setPlan] = useState<any>(null)

  useEffect(() => {
    if (releaseId) relApi.rollback.get(releaseId).then(resp => setPlan(resp.data))
  }, [releaseId])

  if (!plan) return <Card title="回滚方案">加载中...</Card>

  return (
    <Card title="回滚方案详情" extra={
      plan.drill_status === 'NOT_DRILLED' ? <Button type="primary" onClick={() => navigate(`/rel/rollback/${releaseId}/drill`)}>执行演练</Button> : null
    }>
      <Descriptions bordered column={1}>
        <Descriptions.Item label="回滚方案ID">{plan.rollback_id}</Descriptions.Item>
        <Descriptions.Item label="封版ID">{plan.release_id}</Descriptions.Item>
        <Descriptions.Item label="方案哈希">{plan.plan_hash}</Descriptions.Item>
        <Descriptions.Item label="演练状态"><Tag color={plan.drill_status === 'DRILLED_PASS' ? 'green' : plan.drill_status === 'DRILLED_FAIL' ? 'red' : 'blue'}>{plan.drill_status}</Tag></Descriptions.Item>
      </Descriptions>
    </Card>
  )
}