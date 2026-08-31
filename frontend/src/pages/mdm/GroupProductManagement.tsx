import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, Select, Space, Tag, message, Descriptions, InputNumber } from 'antd'
import { PlusOutlined, ReloadOutlined, StopOutlined, BarcodeOutlined } from '@ant-design/icons'
import { groupProductApi, specTemplateApi } from '@/api/mdm'
import type { GroupProduct, GroupSku, GroupCategory, GroupBrand, GroupUnit, SpecTemplate } from '@/api/mdm/types'

export default function GroupProductManagement() {
  const [products, setProducts] = useState<GroupProduct[]>([])
  const [categories, setCategories] = useState<GroupCategory[]>([])
  const [brands, setBrands] = useState<GroupBrand[]>([])
  const [units, setUnits] = useState<GroupUnit[]>([])
  const [specTemplates, setSpecTemplates] = useState<SpecTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [skuModalOpen, setSkuModalOpen] = useState(false)
  const [currentProduct, setCurrentProduct] = useState<GroupProduct | null>(null)
  const [skus, setSkus] = useState<GroupSku[]>([])
  const [skuLoading, setSkuLoading] = useState(false)
  const [form] = Form.useForm()
  const [skuForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [productList, catList, brandList, unitList, templateList] = await Promise.all([
        groupProductApi.list(),
        groupProductApi.listCategories(),
        groupProductApi.listBrands(),
        groupProductApi.listUnits(),
        specTemplateApi.listGroup(),
      ])
      setProducts(productList)
      setCategories(catList)
      setBrands(brandList)
      setUnits(unitList)
      setSpecTemplates(templateList)
    } catch {
      message.error('加载集团商品列表失败')
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
      await groupProductApi.create(values)
      message.success('集团商品创建成功')
      setModalOpen(false)
      form.resetFields()
      loadData()
    } catch {
      message.error('创建失败')
    }
  }

  const handleDisable = async (id: string) => {
    try {
      await groupProductApi.disable(id)
      message.success('集团商品已停用')
      loadData()
    } catch {
      message.error('停用失败')
    }
  }

  const handleManageSkus = async (product: GroupProduct) => {
    setCurrentProduct(product)
    setSkuModalOpen(true)
    setSkuLoading(true)
    try {
      const skuList = await groupProductApi.listSkus(product.group_product_id)
      setSkus(skuList)
    } catch {
      message.error('加载 SKU 列表失败')
    } finally {
      setSkuLoading(false)
    }
  }

  const handleAddSku = async () => {
    if (!currentProduct) return
    const values = await skuForm.validateFields()
    try {
      const payload = {
        ...values,
        barcode_list: values.barcode_list
          ? String(values.barcode_list).split(',').map((s) => s.trim()).filter(Boolean)
          : undefined,
      }
      await groupProductApi.addSku(currentProduct.group_product_id, payload)
      message.success('SKU 添加成功')
      skuForm.resetFields()
      const skuList = await groupProductApi.listSkus(currentProduct.group_product_id)
      setSkus(skuList)
    } catch {
      message.error('SKU 添加失败')
    }
  }

  const productColumns = [
    { title: '商品编码', dataIndex: 'group_product_code', key: 'group_product_code' },
    { title: '商品名称', dataIndex: 'group_product_name', key: 'group_product_name' },
    {
      title: '分类',
      dataIndex: 'group_category_id',
      key: 'group_category_id',
      render: (id: string | null) => categories.find((c) => c.group_category_id === id)?.group_category_name || '-',
    },
    {
      title: '品牌',
      dataIndex: 'group_brand_id',
      key: 'group_brand_id',
      render: (id: string | null) => brands.find((b) => b.group_brand_id === id)?.group_brand_name || '-',
    },
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
    { title: '发布版本', dataIndex: 'published_version', key: 'published_version' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: GroupProduct) => (
        <Space>
          <Button size="small" icon={<BarcodeOutlined />} onClick={() => handleManageSkus(record)}>
            SKU 管理
          </Button>
          {record.status === 'active' && (
            <Button size="small" danger icon={<StopOutlined />} onClick={() => handleDisable(record.group_product_id)}>
              停用
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const skuColumns = [
    { title: 'SKU 编码', dataIndex: 'group_sku_code', key: 'group_sku_code' },
    { title: 'SKU 名称', dataIndex: 'group_sku_name', key: 'group_sku_name' },
    {
      title: '单位',
      dataIndex: 'unit_id',
      key: 'unit_id',
      render: (id: string) => units.find((u) => u.group_unit_id === id)?.group_unit_name || id,
    },
    {
      title: '条码',
      dataIndex: 'barcode_list',
      key: 'barcode_list',
      render: (barcodes: string[] | null) => barcodes?.join(', ') || '-',
    },
    { title: '重量(kg)', dataIndex: 'weight', key: 'weight' },
    { title: '体积(m³)', dataIndex: 'volume', key: 'volume' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={status === 'active' ? 'green' : 'red'}>{status}</Tag>,
    },
  ]

  return (
    <Card>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建集团商品
        </Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>
          刷新
        </Button>
      </Space>
      <Table
        columns={productColumns}
        dataSource={products}
        rowKey="group_product_id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title="新建集团商品"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="group_product_code" label="商品编码" rules={[{ required: true }]}>
            <Input placeholder="如 GP-001" />
          </Form.Item>
          <Form.Item name="group_product_name" label="商品名称" rules={[{ required: true }]}>
            <Input placeholder="如 钢材A001" />
          </Form.Item>
          <Form.Item name="base_unit_id" label="基础计量单位" rules={[{ required: true }]}>
            <Select
              placeholder="选择单位"
              options={units.map((u) => ({ label: u.group_unit_name, value: u.group_unit_id }))}
            />
          </Form.Item>
          <Form.Item name="group_category_id" label="集团分类">
            <Select
              allowClear
              placeholder="选择分类"
              options={categories.map((c) => ({ label: c.group_category_name, value: c.group_category_id }))}
            />
          </Form.Item>
          <Form.Item name="group_brand_id" label="集团品牌">
            <Select
              allowClear
              placeholder="选择品牌"
              options={brands.map((b) => ({ label: b.group_brand_name, value: b.group_brand_id }))}
            />
          </Form.Item>
          <Form.Item name="spec_template_id" label="规格模板">
            <Select
              allowClear
              placeholder="选择规格模板"
              options={specTemplates.map((t) => ({ label: t.template_name, value: t.template_id }))}
            />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={currentProduct ? `SKU 管理 - ${currentProduct.group_product_name}` : 'SKU 管理'}
        open={skuModalOpen}
        onCancel={() => setSkuModalOpen(false)}
        footer={null}
        width={900}
      >
        {currentProduct && (
          <Descriptions size="small" column={3} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="商品编码">{currentProduct.group_product_code}</Descriptions.Item>
            <Descriptions.Item label="发布版本">v{currentProduct.published_version}</Descriptions.Item>
            <Descriptions.Item label="状态">{currentProduct.status}</Descriptions.Item>
          </Descriptions>
        )}
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAddSku}>
            添加 SKU
          </Button>
        </Space>
        <Form form={skuForm} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="group_sku_code" label="SKU 编码" rules={[{ required: true }]}>
            <Input placeholder="如 GS-001" />
          </Form.Item>
          <Form.Item name="group_sku_name" label="SKU 名称" rules={[{ required: true }]}>
            <Input placeholder="如 规格 10mm" />
          </Form.Item>
          <Form.Item name="unit_id" label="单位" rules={[{ required: true }]}>
            <Select
              style={{ width: 100 }}
              placeholder="单位"
              options={units.map((u) => ({ label: u.group_unit_name, value: u.group_unit_id }))}
            />
          </Form.Item>
          <Form.Item name="barcode_list" label="条码(逗号分隔)">
            <Input placeholder="6900000000001,6900000000002" />
          </Form.Item>
          <Form.Item name="weight" label="重量(kg)">
            <InputNumber placeholder="0" />
          </Form.Item>
          <Form.Item name="volume" label="体积(m³)">
            <InputNumber placeholder="0" />
          </Form.Item>
        </Form>
        <Table
          columns={skuColumns}
          dataSource={skus}
          rowKey="group_sku_id"
          loading={skuLoading}
          pagination={{ pageSize: 10 }}
          size="small"
        />
      </Modal>
    </Card>
  )
}
