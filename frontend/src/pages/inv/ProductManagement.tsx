import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { inventoryApi, type Product } from '@/api/inventory'

export default function ProductManagement() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await inventoryApi.listProducts()
      setProducts(data)
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await inventoryApi.createProduct(values)
      message.success('商品-创建成功')
      setModalOpen(false)
      form.resetFields()
      loadData()
    } catch {
      // handled by interceptor
    }
  }

  const columns = [
    { title: '商品编码', dataIndex: 'product_code', key: 'product_code' },
    { title: '商品名称', dataIndex: 'product_name', key: 'product_name' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'red'}>
          {status === 'active' ? '启用' : '停用'}
        </Tag>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建商品
        </Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>
          刷新
        </Button>
      </Space>
      <Table
        columns={columns}
        dataSource={products}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
      <Modal
        title="新建商品"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="product_code" label="商品编码" rules={[{ required: true }]}>
            <Input placeholder="如 P001" />
          </Form.Item>
          <Form.Item name="product_name" label="商品名称" rules={[{ required: true }]}>
            <Input placeholder="如 钢材A001" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}