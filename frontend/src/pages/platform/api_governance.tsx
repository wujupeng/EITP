import { useState, useEffect } from 'react'
import { Card, Table, Tag, Tabs } from 'antd'
import { pltApi } from '@/api/platform'

export default function APIGovernancePage() {
  const [contracts, setContracts] = useState<any[]>([])
  const [rateLimits, setRateLimits] = useState<any[]>([])

  useEffect(() => {
    pltApi.apiGovernance.contracts().then(resp => setContracts(resp.data.items || []))
    pltApi.apiGovernance.rateLimits().then(resp => setRateLimits(resp.data.items || []))
  }, [])

  return (
    <Card title="API 治理">
      <Tabs items={[
        { key: 'contracts', label: '版本契约', children: (
          <Table dataSource={contracts} rowKey="contract_id" columns={[
            { title: 'API路径', dataIndex: 'api_path' },
            { title: '版本', dataIndex: 'version' },
            { title: '变更类型', dataIndex: 'change_type', render: (v: string) => <Tag color={v === 'BREAKING' ? 'red' : v === 'DEPRECATED' ? 'orange' : 'green'}>{v}</Tag> },
            { title: '引入时间', dataIndex: 'introduced_at' },
          ]} />
        )},
        { key: 'limits', label: '限流配置', children: (
          <Table dataSource={rateLimits} rowKey="config_id" columns={[
            { title: 'API路径', dataIndex: 'api_path' },
            { title: 'QPS', dataIndex: 'qps_limit' },
            { title: '突发', dataIndex: 'burst_size' },
            { title: '启用', dataIndex: 'enabled', render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '是' : '否'}</Tag> },
          ]} />
        )},
      ]} />
    </Card>
  )
}