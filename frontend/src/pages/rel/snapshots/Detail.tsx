import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag } from 'antd'
import { relApi } from '@/api/rel'
import { useParams } from 'react-router-dom'

export default function RelSnapshotDetailPage() {
  const { releaseId, snapshotId } = useParams<{ releaseId: string; snapshotId: string }>()
  const [snapshot, setSnapshot] = useState<any>(null)

  useEffect(() => {
    if (releaseId && snapshotId) relApi.snapshot.get(releaseId, snapshotId).then(resp => setSnapshot(resp.data))
  }, [releaseId, snapshotId])

  if (!snapshot) return <Card title="资产快照详情">加载中...</Card>

  return (
    <Card title="资产快照详情">
      <Descriptions bordered column={1}>
        <Descriptions.Item label="快照ID">{snapshot.snapshot_id}</Descriptions.Item>
        <Descriptions.Item label="资产类型">{snapshot.asset_type}</Descriptions.Item>
        <Descriptions.Item label="资产名称">{snapshot.asset_name}</Descriptions.Item>
        <Descriptions.Item label="内容哈希">{snapshot.asset_content_hash}</Descriptions.Item>
        <Descriptions.Item label="归档位置">{snapshot.archive_location}</Descriptions.Item>
        <Descriptions.Item label="大小(bytes)">{snapshot.archive_size_bytes}</Descriptions.Item>
        <Descriptions.Item label="校验状态"><Tag color={snapshot.verification_status === 'VERIFIED' ? 'green' : 'red'}>{snapshot.verification_status}</Tag></Descriptions.Item>
      </Descriptions>
    </Card>
  )
}