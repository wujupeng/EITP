import { useState, useEffect } from 'react'
import { Card, Typography, Table, Button, Modal, Form, Input, Select, Space, Tag, message, Popconfirm } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { client } from '@/api/client'

const { Title, Paragraph } = Typography

interface Tenant {
  id: string
  enterprise_name: string
  status: string
  data_placement: string
  version: number
  idempotency_key: string | null
}

const STATUS_COLORS: Record<string, string> = {
  provisioning: 'processing',
  active: 'success',
  disabled: 'warning',
  deprovisioned: 'default',
  failed: 'error',
}

const STATUS_LABELS: Record<string, string> = {
  provisioning: '开通中',
  active: '正常',
  disabled: '已停用',
  deprovisioned: '已注销',
  failed: '开通失败',
}

export default function TenantManagement() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const fetchTenants = async () => {
    setLoading(true)
    try {
      const response = await client.get<Tenant[]>('/platform/tenants')
      setTenants(response.data)
    } catch {
      message.error('加载租户列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchTenants()
  }, [])

  const handleProvision = async () => {
    const values = await form.validateFields()
    try {
      await client.post('/platform/tenants', values)
      message.success('租户开通请求已提交')
      setModalOpen(false)
      form.resetFields()
      fetchTenants()
    } catch {
      message.error('租户开通失败')
    }
  }

  const handleStatusTransition = async (tenantId: string, action: string, confirmToken?: string) => {
    try {
      await client.post(`/platform/tenants/${tenantId}/status`, { action, confirm_token: confirmToken })
      message.success('状态流转成功')
      fetchTenants()
    } catch {
      message.error('状态流转失败')
    }
  }

  const handleDeprovision = async (tenantId: string) => {
    Modal.confirm({
      title: '二次确认 - 注销租户',
      content: `请输入租户 ID 以确认注销: ${tenantId}`,
      onOk: () => handleStatusTransition(tenantId, 'deprovision', tenantId),
    })
  }

  const columns: ColumnsType<Tenant> = [
    { title: '企业名称', dataIndex: 'enterprise_name', key: 'enterprise_name' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (status: string) => (
      <Tag color={STATUS_COLORS[status]}>{STATUS_LABELS[status] || status}</Tag>
    )},
    { title: '数据放置', dataIndex: 'data_placement', key: 'data_placement' },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: '操作', key: 'action', render: (_, record) => (
      <Space>
        {record.status === 'provisioning' && (
          <Popconfirm title="确认完成开通？" onConfirm={() => handleStatusTransition(record.id, 'provision')}>
            <Button size="small" type="primary">完成开通</Button>
          </Popconfirm>
        )}
        {record.status === 'active' && (
          <Button size="small" onClick={() => handleStatusTransition(record.id, 'disable')}>停用</Button>
        )}
        {record.status === 'disabled' && (
          <>
            <Button size="small" onClick={() => handleStatusTransition(record.id, 'enable')}>恢复</Button>
            <Popconfirm title="确认注销？" onConfirm={() => handleDeprovision(record.id)}>
              <Button size="small" danger>注销</Button>
            </Popconfirm>
          </>
        )}
      </Space>
    )},
  ]

  return (
    <Card>
      <Title level={3}>平台运营 - 租户管理</Title>
      <Paragraph>管理平台承载的所有企业租户：开通、状态流转、查看配置与用量。</Paragraph>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setModalOpen(true)}>开通新租户</Button>
        <Button onClick={fetchTenants}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={tenants} rowKey="id" loading={loading} />
      <Modal title="开通新租户" open={modalOpen} onOk={handleProvision} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="enterprise_name" label="企业名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="idempotency_key" label="幂等键（社会信用代码）" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="admin_email" label="管理员邮箱" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="data_placement" label="数据放置" initialValue="shared_db">
            <Select options={[
              { value: 'shared_db', label: '共享数据库' },
              { value: 'dedicated_db', label: '独立数据库' },
              { value: 'dedicated_instance', label: '独立实例' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
