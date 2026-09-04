import { useState, useEffect } from 'react'
import { Table, Switch, Card, message, Tag } from 'antd'
import { featureSwitchApi } from '@/api/biz-ops'

export default function FeatureSwitches() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const res = await featureSwitchApi.list()
      setData(res.data)
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const handleToggle = async (key: string, enabled: boolean) => {
    try {
      await featureSwitchApi.update(key, { is_enabled: enabled })
      message.success('更新成功')
      loadData()
    } catch {
      // handled by interceptor
    }
  }

  return (
    <Card title="功能开关管理">
      <Table
        loading={loading}
        dataSource={data}
        rowKey="feature_key"
        columns={[
          { title: '功能键', dataIndex: 'feature_key', key: 'feature_key' },
          { title: '作用域', dataIndex: 'scope', key: 'scope' },
          {
            title: '启用状态',
            dataIndex: 'is_enabled',
            key: 'is_enabled',
            render: (v: boolean, r: any) => (
              <Switch checked={v} onChange={(c) => handleToggle(r.feature_key, c)} />
            ),
          },
          {
            title: '有效状态',
            dataIndex: 'effective_is_enabled',
            key: 'effective_is_enabled',
            render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '有效' : '无效'}</Tag>,
          },
          { title: '描述', dataIndex: 'description', key: 'description' },
        ]}
      />
    </Card>
  )
}