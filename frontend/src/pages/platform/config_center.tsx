import { useState, useEffect } from 'react'
import { Card, Table, Tag } from 'antd'
import { pltApi } from '@/api/platform'

export default function ConfigCenterPage() {
  const [revisions, setRevisions] = useState<any[]>([])

  useEffect(() => { pltApi.config.revisions().then(resp => setRevisions(resp.data.items || [])) }, [])

  return (
    <Card title="配置中心">
      <Table dataSource={revisions} rowKey="revision_id" columns={[
        { title: '命名空间', dataIndex: 'namespace', render: (v: string) => <Tag>{v}</Tag> },
        { title: '配置键', dataIndex: 'config_key' },
        { title: '类型', dataIndex: 'value_type', render: (v: string) => <Tag color={v === 'SECRET' ? 'red' : 'blue'}>{v}</Tag> },
        { title: '版本', dataIndex: 'version' },
        { title: '修改人', dataIndex: 'changed_by' },
        { title: '修改时间', dataIndex: 'changed_at' },
      ]} />
    </Card>
  )
}