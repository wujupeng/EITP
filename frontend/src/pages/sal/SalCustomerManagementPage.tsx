import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Tag, Drawer, Steps } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { Customer, CustomerStatus } from '@/types/sal'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', submitted: 'blue', approved: 'cyan',
  active: 'green', disabled: 'red', rejected: 'volcano',
}

const STATUS_STEPS: CustomerStatus[] = ['draft', 'submitted', 'approved', 'active']

export default function SalCustomerManagementPage() {
  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [current, setCurrent] = useState<Customer | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.customers.list()
      setCustomers(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.customers.create(values)
      message.success('客户创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'approve' | 'publish' | 'disable') => {
    try {
      if (action === 'submit') await salApi.customers.submit(id)
      else if (action === 'approve') await salApi.customers.approve(id, { approved: true })
      else if (action === 'publish') await salApi.customers.publish(id)
      else if (action === 'disable') await salApi.customers.disable(id)
      message.success('操作成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '客户编码', dataIndex: 'customer_code', key: 'customer_code' },
    { title: '客户名称', dataIndex: 'customer_name', key: 'customer_name' },
    { title: '类型', dataIndex: 'customer_type', key: 'customer_type' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, record: Customer) => (
        <Space>
          <Button size="small" onClick={() => { setCurrent(record); setDrawerOpen(true) }}>详情</Button>
          {record.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(record.customer_id, 'submit')}>提交</Button>}
          {record.status === 'submitted' && <Button size="small" type="link" onClick={() => handleAction(record.customer_id, 'approve')}>审批</Button>}
          {record.status === 'approved' && <Button size="small" type="link" onClick={() => handleAction(record.customer_id, 'publish')}>发布</Button>}
          {record.status === 'active' && <Button size="small" type="link" danger onClick={() => handleAction(record.customer_id, 'disable')}>停用</Button>}
        </Space>
      ),
    },
  ]

  const currentStep = current ? STATUS_STEPS.indexOf(current.status) : -1

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建客户</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={customers} rowKey="customer_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建客户" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="customer_code" label="客户编码" rules={[{ required: true }]}><Input placeholder="如 C001" /></Form.Item>
          <Form.Item name="customer_name" label="客户名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="customer_type" label="类型" initialValue="enterprise">
            <Select options={[
              { value: 'enterprise', label: '企业' },
              { value: 'individual', label: '个人' },
              { value: 'government', label: '政府' },
              { value: 'partner', label: '合作伙伴' },
            ]} />
          </Form.Item>
          <Form.Item name="tax_id" label="税号"><Input /></Form.Item>
          <Form.Item name="contact_name" label="联系人"><Input /></Form.Item>
          <Form.Item name="contact_phone" label="联系电话"><Input /></Form.Item>
          <Form.Item name="contact_email" label="联系邮箱"><Input /></Form.Item>
        </Form>
      </Modal>
      <Drawer title="客户详情" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={600}>
        {current && (
          <div>
            <DescriptionsCompact customer={current} />
            <Steps
              size="small"
              current={currentStep}
              items={[
                { title: '草稿' },
                { title: '已提交' },
                { title: '已审批' },
                { title: '已发布' },
              ]}
              style={{ marginTop: 16 }}
            />
          </div>
        )}
      </Drawer>
    </div>
  )
}

function DescriptionsCompact({ customer }: { customer: Customer }) {
  return (
    <div>
      <p>编码: {customer.customer_code}</p>
      <p>名称: {customer.customer_name}</p>
      <p>类型: {customer.customer_type}</p>
      <p>状态: <Tag color={STATUS_COLORS[customer.status]}>{customer.status}</Tag></p>
      <p>发布版本: {customer.published_version}</p>
      <p>税号: {customer.tax_id}</p>
      <p>联系人: {customer.contact_name} / {customer.contact_phone}</p>
    </div>
  )
}