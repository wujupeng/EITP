import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Select, Space, Row, Col, Statistic, message } from 'antd'
import { treasuryApi } from '@/api/fin/treasury'
import { formatMoney } from '@/utils/finMoney'

export default function TreasuryAccountsPage() {
  const [data, setData] = useState<any[]>([])
  const [balance, setBalance] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const [accRes, balRes] = await Promise.all([
        treasuryApi.accounts.list(params),
        treasuryApi.balance(params),
      ])
      setData(accRes.data?.items || [])
      setBalance(balRes.data)
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleSearch = async () => {
    const values = await form.validateFields()
    fetchData(values)
  }

  const handleReset = () => {
    form.resetFields()
    fetchData()
  }

  const handleFreeze = async (id: string) => {
    try {
      await treasuryApi.freeze(id, { action: 'FREEZE' })
      message.success('账户冻结成功')
      fetchData()
    } catch {
      message.error('账户冻结失败')
    }
  }

  const columns = [
    { title: '账户号', dataIndex: 'account_number', key: 'account_number' },
    { title: '账户名称', dataIndex: 'account_name', key: 'account_name' },
    { title: '银行', dataIndex: 'bank_name', key: 'bank_name' },
    { title: '币种', dataIndex: 'currency', key: 'currency' },
    { title: '余额', dataIndex: 'balance', key: 'balance', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'ACTIVE' ? 'green' : v === 'FROZEN' ? 'blue' : 'red'}>{v}</Tag> },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => handleFreeze(record.account_id)}>冻结</Button>
    )},
  ]

  return (
    <Card title="资金账户列表">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="bank_name" label="银行">
          <Input placeholder="银行" allowClear />
        </Form.Item>
        <Form.Item name="currency" label="币种">
          <Select placeholder="全部" allowClear style={{ width: 120 }} options={['CNY', 'USD', 'EUR'].map(c => ({ label: c, value: c }))} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
      {balance && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}><Statistic title="总余额" value={formatMoney(balance.total_balance, balance.currency)} /></Col>
          <Col span={8}><Statistic title="可用余额" value={formatMoney(balance.available_balance, balance.currency)} valueStyle={{ color: '#52c41a' }} /></Col>
          <Col span={8}><Statistic title="冻结金额" value={formatMoney(balance.frozen_balance, balance.currency)} valueStyle={{ color: '#1890ff' }} /></Col>
        </Row>
      )}
      <Table columns={columns} dataSource={data} rowKey="account_id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  )
}