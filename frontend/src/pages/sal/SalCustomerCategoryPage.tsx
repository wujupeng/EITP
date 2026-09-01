import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { CustomerCategory } from '@/types/sal'

export default function SalCustomerCategoryPage() {
  const [categories, setCategories] = useState<CustomerCategory[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.categories.list()
      setCategories(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.categories.create(values)
      message.success('客户分类创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleDisable = async (id: string) => {
    try {
      await salApi.categories.disable(id)
      message.success('停用成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '分类编码', dataIndex: 'category_code', key: 'category_code' },
    { title: '分类名称', dataIndex: 'category_name', key: 'category_name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={s === 'active' ? 'green' : 'red'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: CustomerCategory) => (
        <Space>
          {r.status === 'active' && <Button size="small" type="link" danger onClick={() => handleDisable(r.category_id)}>停用</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建分类</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={categories} rowKey="category_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建客户分类" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={500}>
        <Form form={form} layout="vertical">
          <Form.Item name="category_code" label="分类编码" rules={[{ required: true }]}><Input placeholder="如 VIP" /></Form.Item>
          <Form.Item name="category_name" label="分类名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}