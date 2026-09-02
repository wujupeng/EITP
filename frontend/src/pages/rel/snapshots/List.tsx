import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button } from 'antd'
import { relApi } from '@/api/rel'
import { useParams } from 'react-router-dom'

export default function RelSnapshotListPage() {
  const { releaseId } = useParams<{ releaseId: string }>()
  const [snapshots, setSnapshots] = useState<any[]>([])

  useEffect(() => {
    if (releaseId) relApi.snapshot.list(releaseId).then(resp => setSnapshots(resp.data?.snapshots || []))
  }, [releaseId])

  const columns = [
    { title: '资产类型', dataIndex: 'asset_type', key: 'asset_type' },
    { title: '资产名称', dataIndex: 'asset_name', key: 'asset_name' },
    { title: '内容哈希', dataIndex: 'asset_content_hash', key: 'asset_content_hash', render: (v: string) => v?.substring(0, 16) + '...' },
    { title: '大小(bytes)', dataIndex: 'archive_size_bytes', key: 'archive_size_bytes' },
    { title: '校验状态', dataIndex: 'verification_status', key: 'verification_status', render: (v: string) => (
      <Tag color={v === 'VERIFIED' ? 'green' : 'red'}>{v}</Tag>
    )},
  ]

  return (
    <Card title={`资产快照 - ${releaseId}`} extra={<Button onClick={() => relApi.snapshot.verifyHash(releaseId!)}>校验哈希</Button>}>
      <Table columns={columns} dataSource={snapshots} rowKey="snapshot_id" pagination={false} />
    </Card>
  )
}