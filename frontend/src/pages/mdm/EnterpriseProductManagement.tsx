import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, Select, Space, Tag, message, Tabs } from 'antd'
import { PlusOutlined, ReloadOutlined, LinkOutlined, DisconnectOutlined } from '@ant-design/icons'
import { enterpriseProductApi, groupProductApi, referenceApi } from '@/api/mdm'
import type { EnterpriseProduct, GroupProduct, ProductReference } from '@/api/mdm/types'

export default function EnterpriseProductManagement() {
  const [enterpriseProducts, setEnterpriseProducts] = useState<EnterpriseProduct[]>([])
  const [groupProducts, setGroupProducts] = useState<GroupProduct[]>([])
  const [references, setReferences] = useState<ProductReference[]>([])
  const [loading, setLoading] = useState(false)
  const [referenceModalOpen, setReferenceModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [epList, gpList, refList] = await Promise.all([
        enterpriseProductApi.list(),
        groupProductApi.list(),
        referenceApi.list(),
      ])
      setEnterpriseProducts(epList)
      setGroupProducts(gpList)
      setReferences(refList)
    } catch {
      message.error('加载企业商品列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleReference = async () => {
    const values = await form.validateFields()
    try {
      await enterpriseProductApi.reference({
        group_product_id: values.group_product_id,
        enterprise_product_code: values.enterprise_product_code,
        enterprise_product_name: values.enterprise_product_name,
        enterprise_category_id: values.enterprise_category_id,
      })
      message.success('商品引用成功')
      setReferenceModalOpen(false)
      form.resetFields()
      loadData()
    } catch {
      message.error('引用失败')
    }
  }

  const handleReleaseReference = async (id: string) => {
    try {
      await enterpriseProductApi.releaseReference(id)
      message.success('引用已解除')
      loadData()
    } catch {
      message.error('解除引用失败')
    }
  }

  const epColumns = [
    { title: '企业商品编码', dataIndex: 'enterprise_product_code', key: 'enterprise_product_code' },
    { title: '企业商品名称', dataIndex: 'enterprise_product_name', key: 'enterprise_product_name' },
    {
      title: '集团商品',
      dataIndex: 'group_product_id',
      key: 'group_product_id',
      render: (id: string) => groupProducts.find((g) => g.group_product_id === id)?.group_product_name || id,
    },
    {
      title: '引用状态',
      dataIndex: 'reference_status',
      key: 'reference_status',
      render: (status: string) => {
        const colorMap: Record<string, string> = { active: 'green', reference_released: 'orange', source_disabled: 'red' }
        return <Tag color={colorMap[status] || 'default'}>{status}</Tag>
      },
    },
    { title: '发布版本', dataIndex: 'published_version', key: 'published_version' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: EnterpriseProduct) =>
        record.reference_status === 'active' && (
          <Button size="small" danger icon={<DisconnectOutlined />} onClick={() => handleReleaseReference(record.enterprise_product_id)}>
            解除引用
          </Button>
        ),
    },
  ]

  const gpColumns = [
    { title: '集团商品编码', dataIndex: 'group_product_code', key: 'group_product_code' },
    { title: '集团商品名称', dataIndex: 'group_product_name', key: 'group_product_name' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={status === 'active' ? 'green' : 'red'}>{status}</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: GroupProduct) => (
        <Button
          size="small"
          type="primary"
          icon={<LinkOutlined />}
          onClick={() => {
            form.setFieldsValue({
              group_product_id: record.group_product_id,
              enterprise_product_code: `EP-${record.group_product_code}`,
              enterprise_product_name: record.group_product_name,
            })
            setReferenceModalOpen(true)
          }}
        >
          引用
        </Button>
      ),
    },
  ]

  const refColumns = [
    { title: '引用ID', dataIndex: 'reference_id', key: 'reference_id', render: (id: string) => id.substring(0, 8) + '...' },
    {
      title: '集团商品',
      dataIndex: 'group_product_id',
      key: 'group_product_id',
      render: (id: string) => groupProducts.find((g) => g.group_product_id === id)?.group_product_name || id,
    },
    {
      title: '企业商品',
      dataIndex: 'enterprise_product_id',
      key: 'enterprise_product_id',
      render: (id: string) => enterpriseProducts.find((e) => e.enterprise_product_id === id)?.enterprise_product_name || id,
    },
    {
      title: '引用状态',
      dataIndex: 'reference_status',
      key: 'reference_status',
      render: (status: string) => <Tag color={status === 'active' ? 'green' : 'red'}>{status}</Tag>,
    },
    { title: '引用时间', dataIndex: 'referenced_at', key: 'referenced_at' },
  ]

  return (
    <Card>
      <Tabs
        items={[
          {
            key: 'enterprise-products',
            label: '企业商品',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setReferenceModalOpen(true)}>
                    引用集团商品
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
                </Space>
                <Table columns={epColumns} dataSource={enterpriseProducts} rowKey="enterprise_product_id" loading={loading} pagination={{ pageSize: 20 }} />
              </>
            ),
          },
          {
            key: 'available-group-products',
            label: '可引用集团商品',
            children: (
              <>
                <Button icon={<ReloadOutlined />} onClick={loadData} style={{ marginBottom: 16 }}>刷新</Button>
                <Table columns={gpColumns} dataSource={groupProducts.filter((g) => g.status === 'active')} rowKey="group_product_id" loading={loading} pagination={{ pageSize: 20 }} />
              </>
            ),
          },
          {
            key: 'references',
            label: '引用关系',
            children: (
              <>
                <Button icon={<ReloadOutlined />} onClick={loadData} style={{ marginBottom: 16 }}>刷新</Button>
                <Table columns={refColumns} dataSource={references} rowKey="reference_id" loading={loading} pagination={{ pageSize: 20 }} />
              </>
            ),
          },
        ]}
      />

      <Modal title="引用集团商品" open={referenceModalOpen} onOk={handleReference} onCancel={() => setReferenceModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="group_product_id" label="集团商品" rules={[{ required: true }]}>
            <Select
              placeholder="选择集团商品"
              options={groupProducts.filter((g) => g.status === 'active').map((g) => ({
                label: `${g.group_product_code} - ${g.group_product_name}`,
                value: g.group_product_id,
              }))}
            />
          </Form.Item>
          <Form.Item name="enterprise_product_code" label="企业商品编码" rules={[{ required: true }]}>
            <Input placeholder="如 EP-001" />
          </Form.Item>
          <Form.Item name="enterprise_product_name" label="企业商品名称">
            <Input placeholder="如 企业商品名称" />
          </Form.Item>
          <Form.Item name="enterprise_category_id" label="企业分类">
            <Input placeholder="企业分类ID（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
