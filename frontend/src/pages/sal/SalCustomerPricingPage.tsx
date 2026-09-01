import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, message, Space, Tag } from 'antd'
import { ReloadOutlined, SettingOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { Customer, CustomerPricing, PriceType } from '@/types/sal'

const PRICE_TYPE_COLORS: Record<string, string> = {
  promotion: 'red', agreement: 'blue', discount: 'cyan', standard: 'default',
}

export default function SalCustomerPricingPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [pricings, setPricings] = useState<CustomerPricing[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [currentId, setCurrentId] = useState('')
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
    setModalOpen(true)
    form.resetFields()
    try {
      const data = await salApi.pricing.list(customerId)
      setPricings(data)
    } catch {
      setPricings([])
    }
  }

  const handleAdd = async () => {
    const values = await form.validateFields()
    try {
      await salApi.pricing.set(currentId, values)
      message.success('价格体系配置成功')
      form.resetFields()
      const data = await salApi.pricing.list(currentId)
      setPricings(data)
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
        <Button size="small" icon={<SettingOutlined />} onClick={() => openConfig(r.customer_id)}>配置价格体系</Button>
      ),
    },
  ]

  const pricingColumns = [
    { title: 'SKU ID', dataIndex: 'enterprise_sku_id', key: 'enterprise_sku_id' },
    { title: '价格类型', dataIndex: 'price_type', key: 'price_type',
      render: (s: string) => <Tag color={PRICE_TYPE_COLORS[s] || 'default'}>{s}</Tag> },
    { title: '协议价', dataIndex: 'agreement_price', key: 'agreement_price' },
    { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate' },
    { title: '优先级', dataIndex: 'priority', key: 'priority' },
    { title: '有效期', key: 'valid', render: (_: unknown, r: CustomerPricing) => `${r.valid_from || '-'} ~ ${r.valid_until || '-'}` },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={customers} rowKey="customer_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="价格体系配置" open={modalOpen} onCancel={() => setModalOpen(false)} width={800} footer={null}>
        <Table columns={pricingColumns} dataSource={pricings} rowKey="pricing_id" pagination={{ pageSize: 5 }} style={{ marginBottom: 16 }} />
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="enterprise_sku_id" label="SKU ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="price_type" label="价格类型" rules={[{ required: true }]} initialValue="standard">
            <Select options={[
              { value: 'agreement' as PriceType, label: '协议价' },
              { value: 'discount' as PriceType, label: '折扣' },
              { value: 'promotion' as PriceType, label: '促销' },
              { value: 'standard' as PriceType, label: '标准' },
            ]} />
          </Form.Item>
          <Form.Item name="agreement_price" label="协议价"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="discount_rate" label="折扣率"><InputNumber min={0} max={1} step={0.01} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="priority" label="优先级"><InputNumber min={1} max={10} style={{ width: '100%' }} /></Form.Item>
          <Button type="primary" htmlType="submit">新增价格配置</Button>
        </Form>
      </Modal>
    </div>
  )
}