import { useState, useEffect } from 'react'
import { Table, Card, Tag, Tabs } from 'antd'
import { businessRuleApi, pricingStrategyApi, taxConfigApi, inventoryStrategyApi } from '@/api/biz-ops'

export default function StrategyManagement() {
  const [rules, setRules] = useState<any[]>([])
  const [pricing, setPricing] = useState<any[]>([])
  const [taxConfigs, setTaxConfigs] = useState<any[]>([])
  const [invStrategies, setInvStrategies] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [r, p, t, i] = await Promise.all([
          businessRuleApi.list(),
          pricingStrategyApi.list(),
          taxConfigApi.list(),
          inventoryStrategyApi.list(),
        ])
        setRules(r.data)
        setPricing(p.data)
        setTaxConfigs(t.data)
        setInvStrategies(i.data)
      } catch {
        // handled by interceptor
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <Card title="策略管理">
      <Tabs
        items={[
          {
            key: 'rules',
            label: '业务规则',
            children: (
              <Table
                loading={loading}
                dataSource={rules}
                rowKey="rule_key"
                columns={[
                  { title: '规则键', dataIndex: 'rule_key' },
                  { title: '名称', dataIndex: 'rule_name' },
                  { title: '类型', dataIndex: 'rule_type' },
                  { title: '优先级', dataIndex: 'priority' },
                  {
                    title: '状态',
                    dataIndex: 'is_active',
                    render: (v: boolean) => <Tag color={v ? 'green' : 'red'}>{v ? '启用' : '停用'}</Tag>,
                  },
                ]}
              />
            ),
          },
          {
            key: 'pricing',
            label: '定价策略',
            children: (
              <Table
                loading={loading}
                dataSource={pricing}
                rowKey="strategy_key"
                columns={[
                  { title: '策略键', dataIndex: 'strategy_key' },
                  { title: '名称', dataIndex: 'strategy_name' },
                  { title: '类型', dataIndex: 'strategy_type' },
                  { title: '目标', dataIndex: 'target_ref' },
                  { title: '优先级', dataIndex: 'priority' },
                ]}
              />
            ),
          },
          {
            key: 'tax',
            label: '税务配置',
            children: (
              <Table
                loading={loading}
                dataSource={taxConfigs}
                rowKey="config_key"
                columns={[
                  { title: '配置键', dataIndex: 'config_key' },
                  { title: '名称', dataIndex: 'config_name' },
                  { title: '含税标志', dataIndex: 'tax_flag' },
                  { title: '方向', dataIndex: 'direction' },
                ]}
              />
            ),
          },
          {
            key: 'inventory',
            label: '库存策略',
            children: (
              <Table
                loading={loading}
                dataSource={invStrategies}
                rowKey="strategy_key"
                columns={[
                  { title: '策略键', dataIndex: 'strategy_key' },
                  { title: '名称', dataIndex: 'strategy_name' },
                  { title: '类型', dataIndex: 'strategy_type' },
                  { title: '目标', dataIndex: 'target_ref' },
                ]}
              />
            ),
          },
        ]}
      />
    </Card>
  )
}