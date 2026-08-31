import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, Space, Tag, message, Tabs, Tree, InputNumber, Typography } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { groupProductApi } from '@/api/mdm'
import type { GroupCategory, GroupBrand, GroupUnit } from '@/api/mdm/types'

const { Text } = Typography

export default function GroupCategoryBrandPage() {
  const [categories, setCategories] = useState<GroupCategory[]>([])
  const [brands, setBrands] = useState<GroupBrand[]>([])
  const [units, setUnits] = useState<GroupUnit[]>([])
  const [loading, setLoading] = useState(false)
  const [brandModalOpen, setBrandModalOpen] = useState(false)
  const [unitModalOpen, setUnitModalOpen] = useState(false)
  const [brandForm] = Form.useForm()
  const [unitForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [catList, brandList, unitList] = await Promise.all([
        groupProductApi.listCategories(),
        groupProductApi.listBrands(),
        groupProductApi.listUnits(),
      ])
      setCategories(catList)
      setBrands(brandList)
      setUnits(unitList)
    } catch {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreateBrand = async () => {
    const values = await brandForm.validateFields()
    try {
      await groupProductApi.createBrand(values)
      message.success('品牌创建成功')
      setBrandModalOpen(false)
      brandForm.resetFields()
      loadData()
    } catch {
      message.error('创建失败')
    }
  }

  const handleCreateUnit = async () => {
    const values = await unitForm.validateFields()
    try {
      await groupProductApi.createUnit(values)
      message.success('计量单位创建成功')
      setUnitModalOpen(false)
      unitForm.resetFields()
      loadData()
    } catch {
      message.error('创建失败')
    }
  }

  const buildCategoryTree = (cats: GroupCategory[]) => {
    const map = new Map<string, GroupCategory & { children?: any[] }>()
    const roots: (GroupCategory & { children?: any[] })[] = []
    cats.forEach((c) => map.set(c.group_category_id, { ...c, children: [] }))
    cats.forEach((c) => {
      const node = map.get(c.group_category_id)!
      if (c.parent_category_id && map.has(c.parent_category_id)) {
        map.get(c.parent_category_id)!.children!.push(node)
      } else {
        roots.push(node)
      }
    })
    return roots
  }

  const treeData = buildCategoryTree(categories).map((node) => ({
    key: node.group_category_id,
    title: (
      <Space>
        <Text strong>{node.group_category_name}</Text>
        <Tag>{node.group_category_code}</Tag>
        <Text type="secondary">层级 {node.level}</Text>
      </Space>
    ),
    children: node.children?.map((child: any) => ({
      key: child.group_category_id,
      title: (
        <Space>
          <Text>{child.group_category_name}</Text>
          <Tag>{child.group_category_code}</Tag>
        </Space>
      ),
    })),
  }))

  const brandColumns = [
    { title: '品牌编码', dataIndex: 'group_brand_code', key: 'group_brand_code' },
    { title: '品牌名称', dataIndex: 'group_brand_name', key: 'group_brand_name' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={status === 'active' ? 'green' : 'red'}>{status}</Tag>,
    },
  ]

  const unitColumns = [
    { title: '单位编码', dataIndex: 'group_unit_code', key: 'group_unit_code' },
    { title: '单位名称', dataIndex: 'group_unit_name', key: 'group_unit_name' },
    {
      title: '基础单位',
      dataIndex: 'is_base_unit',
      key: 'is_base_unit',
      render: (isBase: boolean) => (isBase ? <Tag color="blue">是</Tag> : '否'),
    },
  ]

  return (
    <Card>
      <Tabs
        items={[
          {
            key: 'categories',
            label: '集团分类',
            children: (
              <>
                <Button icon={<ReloadOutlined />} onClick={loadData} style={{ marginBottom: 16 }}>
                  刷新
                </Button>
                <Tree treeData={treeData} defaultExpandAll />
              </>
            ),
          },
          {
            key: 'brands',
            label: '集团品牌',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setBrandModalOpen(true)}>
                    新建品牌
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={loadData}>
                    刷新
                  </Button>
                </Space>
                <Table
                  columns={brandColumns}
                  dataSource={brands}
                  rowKey="group_brand_id"
                  loading={loading}
                  pagination={{ pageSize: 20 }}
                />
              </>
            ),
          },
          {
            key: 'units',
            label: '计量单位',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setUnitModalOpen(true)}>
                    新建单位
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={loadData}>
                    刷新
                  </Button>
                </Space>
                <Table
                  columns={unitColumns}
                  dataSource={units}
                  rowKey="group_unit_id"
                  loading={loading}
                  pagination={{ pageSize: 20 }}
                />
              </>
            ),
          },
        ]}
      />

      <Modal
        title="新建集团品牌"
        open={brandModalOpen}
        onOk={handleCreateBrand}
        onCancel={() => setBrandModalOpen(false)}
      >
        <Form form={brandForm} layout="vertical">
          <Form.Item name="group_brand_code" label="品牌编码" rules={[{ required: true }]}>
            <Input placeholder="如 BRAND-001" />
          </Form.Item>
          <Form.Item name="group_brand_name" label="品牌名称" rules={[{ required: true }]}>
            <Input placeholder="如 华为" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="新建计量单位"
        open={unitModalOpen}
        onOk={handleCreateUnit}
        onCancel={() => setUnitModalOpen(false)}
      >
        <Form form={unitForm} layout="vertical">
          <Form.Item name="group_unit_code" label="单位编码" rules={[{ required: true }]}>
            <Input placeholder="如 KG" />
          </Form.Item>
          <Form.Item name="group_unit_name" label="单位名称" rules={[{ required: true }]}>
            <Input placeholder="如 千克" />
          </Form.Item>
          <Form.Item name="is_base_unit" label="是否基础单位">
            <InputNumber min={0} max={1} placeholder="1=是, 0=否" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}