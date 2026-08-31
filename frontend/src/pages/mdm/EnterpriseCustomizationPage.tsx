import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, Select, Space, Tag, message, InputNumber } from 'antd'
import { PlusOutlined, ReloadOutlined, EditOutlined } from '@ant-design/icons'
import { enterpriseProductApi, customizationApi } from '@/api/mdm'
import type { EnterpriseProduct, Customization } from '@/api/mdm/types'


export default function EnterpriseCustomizationPage() {
  const [enterpriseProducts, setEnterpriseProducts] = useState<EnterpriseProduct[]>([])
  const [customizations, setCustomizations] = useState<Customization[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [currentProductId, setCurrentProductId] = useState<string | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const epList = await enterpriseProductApi.list()
      setEnterpriseProducts(epList)
      const customList = await Promise.all(
        epList.map((ep) => customizationApi.get(ep.enterprise_product_id).catch(() => null))
      )
      setCustomizations(customList.filter((c): c is Customization => c !== null))
    } catch {
      message.error('加载定制列表失败')
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
      await customizationApi.create({
        enterprise_product_id: currentProductId!,
        enterprise_sku_id: values.enterprise_sku_id,
        sales_price: values.sales_price,
        purchase_price: values.purchase_price,
        inventory_strategy: values.inventory_strategy,
        safety_stock: values.safety_stock,
        cost_model: values.cost_model,
        custom_attributes: values.custom_attributes ? JSON.parse(values.custom_attributes) : undefined,
      })
      message.success('定制创建成功')
      setModalOpen(false)
      form.resetFields()
      setCurrentProductId(null)
      loadData()
    } catch {
      message.error('创建失败')
    }
  }

  const handleEdit = (productId: string) => {
    setCurrentProductId(productId)
    const ep = enterpriseProducts.find((e) => e.enterprise_product_id === productId)
    if (ep) {
      form.setFieldsValue({ enterprise_product_id: productId })
    }
    setModalOpen(true)
  }

  const columns = [
    {
      title: '企业商品编码',
      key: 'enterprise_product_code',
      render: (_: unknown, record: Customization) =>
        enterpriseProducts.find((e) => e.enterprise_product_id === record.enterprise_product_id)?.enterprise_product_code || record.enterprise_product_id,
    },
    {
      title: '企业商品名称',
      key: 'enterprise_product_name',
      render: (_: unknown, record: Customization) =>
        enterpriseProducts.find((e) => e.enterprise_product_id === record.enterprise_product_id)?.enterprise_product_name || '-',
    },
    {
      title: '销售价',
      dataIndex: 'sales_price',
      key: 'sales_price',
      render: (v: number | null) => v != null ? `¥${v.toFixed(2)}` : '-',
    },
    {
      title: '采购价',
      dataIndex: 'purchase_price',
      key: 'purchase_price',
      render: (v: number | null) => v != null ? `¥${v.toFixed(2)}` : '-',
    },
    {
      title: '库存策略',
      dataIndex: 'inventory_strategy',
      key: 'inventory_strategy',
      render: (v: string | null) => v ? <Tag color="blue">{v}</Tag> : '-',
    },
    {
      title: '安全库存',
      dataIndex: 'safety_stock',
      key: 'safety_stock',
    },
    {
      title: '计价策略',
      dataIndex: 'cost_model',
      key: 'cost_model',
      render: (v: string | null) => v ? <Tag>{v}</Tag> : '-',
    },
    { title: '版本', dataIndex: 'version', key: 'version' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Customization) => (
        <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record.enterprise_product_id)}>
          编辑
        </Button>
      ),
    },
  ]

  return (
    <Card>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建定制
        </Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>
          刷新
        </Button>
      </Space>
      <Table
        columns={columns}
        dataSource={customizations}
        rowKey="customization_id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title={currentProductId ? '编辑定制' : '新建定制'}
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => { setModalOpen(false); form.resetFields(); setCurrentProductId(null) }}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="enterprise_product_id" label="企业商品" rules={[{ required: true }]}>
            <Select
              placeholder="选择企业商品"
              options={enterpriseProducts.map((ep) => ({
                label: `${ep.enterprise_product_code} - ${ep.enterprise_product_name || '未命名'}`,
                value: ep.enterprise_product_id,
              }))}
              onChange={(v) => setCurrentProductId(v)}
            />
          </Form.Item>
          <Form.Item name="enterprise_sku_id" label="企业 SKU">
            <Input placeholder="企业 SKU ID（可选）" />
          </Form.Item>
          <Form.Item name="sales_price" label="销售价 (¥)">
            <InputNumber min={0} step={0.01} placeholder="0.00" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="purchase_price" label="采购价 (¥)">
            <InputNumber min={0} step={0.01} placeholder="0.00" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="inventory_strategy" label="库存策略">
            <Select
              allowClear
              options={[
                { label: 'FIFO（先进先出）', value: 'fifo' },
                { label: 'LIFO（后进先出）', value: 'lifo' },
                { label: '批次管理', value: 'batch' },
                { label: '序列号管理', value: 'serial' },
              ]}
            />
          </Form.Item>
          <Form.Item name="safety_stock" label="安全库存">
            <InputNumber min={0} placeholder="0" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="cost_model" label="计价策略">
            <Select
              allowClear
              options={[
                { label: '加权平均', value: 'weighted_average' },
                { label: '移动平均', value: 'moving_average' },
                { label: '先进先出', value: 'fifo' },
                { label: '后进先出', value: 'lifo' },
                { label: '标准成本', value: 'standard' },
              ]}
            />
          </Form.Item>
          <Form.Item name="custom_attributes" label="企业级属性 (JSON)">
            <Input.TextArea rows={3} placeholder='{"color":"红","size":"L"}' />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}