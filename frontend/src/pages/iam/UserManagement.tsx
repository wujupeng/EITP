import { useState, useEffect } from 'react'
import { Card, Typography, Table, Button, Modal, Form, Input, Space, Tag, message, Popconfirm } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { client } from '@/api/client'
import { useAuthStore } from '@/store/auth'

const { Title, Paragraph } = Typography

interface User {
  id: string
  username: string
  email: string | null
  phone: string | null
  real_name: string | null
  account_status: string
  is_tenant_admin: boolean
}

const STATUS_COLORS: Record<string, string> = {
  active: 'success',
  pending_activation: 'processing',
  locked: 'warning',
  disabled: 'default',
  deactivated: 'error',
}

const STATUS_LABELS: Record<string, string> = {
  active: '正常',
  pending_activation: '待激活',
  locked: '已锁定',
  disabled: '已停用',
  deactivated: '已注销',
}

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const tenantId = useAuthStore((s) => s.tenantId)

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const response = await client.get<User[]>('/iam/users')
      setUsers(response.data)
    } catch {
      message.error('加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [tenantId])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await client.post('/iam/users', values)
      message.success('用户创建成功')
      setModalOpen(false)
      form.resetFields()
      fetchUsers()
    } catch {
      message.error('用户创建失败')
    }
  }

  const handleDisable = async (userId: string) => {
    try {
      await client.patch(`/iam/users/${userId}/disable`)
      message.success('用户已停用')
      fetchUsers()
    } catch {
      message.error('操作失败')
    }
  }

  const handleEnable = async (userId: string) => {
    try {
      await client.patch(`/iam/users/${userId}/enable`)
      message.success('用户已启用')
      fetchUsers()
    } catch {
      message.error('操作失败')
    }
  }

  const columns: ColumnsType<User> = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    { title: '状态', dataIndex: 'account_status', key: 'account_status', render: (status: string) => (
      <Tag color={STATUS_COLORS[status]}>{STATUS_LABELS[status] || status}</Tag>
    )},
    { title: '租户管理员', dataIndex: 'is_tenant_admin', key: 'is_tenant_admin', render: (v: boolean) => v ? <Tag color="blue">是</Tag> : '否' },
    { title: '操作', key: 'action', render: (_, record) => (
      <Space>
        {record.account_status === 'active' && (
          <Popconfirm title="确认停用？" onConfirm={() => handleDisable(record.id)}>
            <Button size="small">停用</Button>
          </Popconfirm>
        )}
        {record.account_status === 'disabled' && (
          <Button size="small" onClick={() => handleEnable(record.id)}>启用</Button>
        )}
      </Space>
    )},
  ]

  return (
    <Card>
      <Title level={3}>用户管理</Title>
      <Paragraph>管理本租户的用户账号：创建、停用、启用、重置密码。</Paragraph>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setModalOpen(true)}>创建用户</Button>
        <Button onClick={fetchUsers}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={users} rowKey="id" loading={loading} />
      <Modal title="创建用户" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 12 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="email" label="邮箱">
            <Input />
          </Form.Item>
          <Form.Item name="real_name" label="真实姓名">
            <Input />
          </Form.Item>
          <Form.Item name="is_tenant_admin" label="租户管理员">
            <Input type="checkbox" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}