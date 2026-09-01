import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, InputNumber, Select, message, Space, Tag } from 'antd'
import { ReloadOutlined, SettingOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { CreditLimit, Customer, OverCreditStrategy } from '@/types/sal'

export default function SalCreditLimitPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [currentId, setCurrentId] = useState('')
  const [current, setCurrent] = useState<CreditLimit | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.customers.list()
      setCustomers(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const openConfig = async (customerId: string) => {
    setCurrentId(customerId)
    try {
      const credit = await salApi.credit.get(customerId)
      setCurrent(credit)
      form.setFieldsValue({
        total_limit: credit.total_limit,
        credit_period_days: credit.credit_period_days,
        over_credit_strategy: credit.over_credit_strategy,
      })
    } catch {
      form.resetFields()
      setCurrent(null)
    }
    setModalOpen(true)
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    try {
      await salApi.credit.set(currentId, values)
      message.success('信用额度配置成功')
      setModalOpen(false); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '客户编码', dataIndex: 'customer_code', key: 'customer_code' },
    { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'active' ? 'green' : 'default'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: Customer) => (
        <Button size="small" icon={<SettingOutlined />} onClick={() => openConfig(r.customer_id)}>配置信用额度</Button>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={customers} rowKey="customer_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="信用额度配置" open={modalOpen} onOk={handleSave} onCancel={() => setModalOpen(false)} width={500}>
        {current && (
          <div style={{ marginBottom: 16, padding: 12, background: '#fafafa' }}>
            <Space>
              <Tag color="blue">已用: {current.used_amount}</Tag>
              <Tag color="green">可用: {current.available_amount}</Tag>
            </Space>
          </div>
        )}
        <Form form={form} layout="vertical">
          <Form.Item name="total_limit" label="总额度" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="credit_period_days" label="信用周期(天)" rules={[{ required: true }]}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="over_credit_strategy" label="超信用策略" rules={[{ required: true }]} initialValue="block">
            <Select options={[
              { value: 'block' as OverCreditStrategy, label: '阻止' },
              { value: 'warn' as OverCreditStrategy, label: '警告' },
              { value: 'special_approval' as OverCreditStrategy, label: '特批' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}