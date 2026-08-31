import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, Select, Space, Tag, message, Tabs, InputNumber, Typography, Checkbox } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { attributeTemplateApi } from '@/api/mdm'
import type { AttributeTemplate } from '@/api/mdm/types'

const { Text } = Typography

export default function AttributeTemplateManagement() {
  const [groupTemplates, setGroupTemplates] = useState<AttributeTemplate[]>([])
  const [enterpriseTemplates, setEnterpriseTemplates] = useState<AttributeTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [groupList, enterpriseList] = await Promise.all([
        attributeTemplateApi.listGroup(),
        attributeTemplateApi.listEnterprise(),
      ])
      setGroupTemplates(groupList)
      setEnterpriseTemplates(enterpriseList)
    } catch {
      message.error('加载属性模板列表失败')
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
      await attributeTemplateApi.create({
        template_code: values.template_code,
        template_name: values.template_name,
        template_level: values.template_level,
        attribute_type: values.attribute_type,
        is_required: values.is_required || false,
        enum_values: values.enum_values ? String(values.enum_values).split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        min_value: values.min_value,
        max_value: values.max_value,
      })
      message.success('属性模板创建成功')
      setModalOpen(false)
      form.resetFields()
      loadData()
    } catch {
      message.error('创建失败')
    }
  }

  const columns = [
    { title: '模板编码', dataIndex: 'template_code', key: 'template_code' },
    { title: '模板名称', dataIndex: 'template_name', key: 'template_name' },
    {
      title: '级别',
      dataIndex: 'template_level',
      key: 'template_level',
      render: (level: string) => (
        <Tag color={level === 'group' ? 'blue' : 'green'}>{level === 'group' ? '集团级' : '企业级'}</Tag>
      ),
    },
    {
      title: '属性类型',
      dataIndex: 'attribute_type',
      key: 'attribute_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = { text: '文本', number: '数字', enum: '枚举', date: '日期', boolean: '布尔' }
        return <Tag>{typeMap[type] || type}</Tag>
      },
    },
    {
      title: '必填',
      dataIndex: 'is_required',
      key: 'is_required',
      render: (required: boolean) => (required ? <Tag color="orange">必填</Tag> : '否'),
    },
    {
      title: '枚举值',
      dataIndex: 'enum_values',
      key: 'enum_values',
      render: (values: string[] | null) => values?.join(', ') || '-',
    },
    {
      title: '数值范围',
      key: 'range',
      render: (_: unknown, record: AttributeTemplate) =>
        record.min_value != null || record.max_value != null ? (
          <Text type="secondary">{record.min_value ?? '-∞'} ~ {record.max_value ?? '+∞'}</Text>
        ) : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={status === 'active' ? 'green' : 'red'}>{status}</Tag>,
    },
  ]

  return (
    <Card>
      <Tabs
        items={[
          {
            key: 'group',
            label: '集团级属性模板',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.setFieldsValue({ template_level: 'group' }); setModalOpen(true) }}>
                    新建集团级模板
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
                </Space>
                <Table columns={columns} dataSource={groupTemplates} rowKey="template_id" loading={loading} pagination={{ pageSize: 20 }} />
              </>
            ),
          },
          {
            key: 'enterprise',
            label: '企业级属性模板',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.setFieldsValue({ template_level: 'enterprise' }); setModalOpen(true) }}>
                    新建企业级模板
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
                </Space>
                <Table columns={columns} dataSource={enterpriseTemplates} rowKey="template_id" loading={loading} pagination={{ pageSize: 20 }} />
              </>
            ),
          },
        ]}
      />

      <Modal title="新建属性模板" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="template_code" label="模板编码" rules={[{ required: true }]}>
            <Input placeholder="如 ATTR-001" />
          </Form.Item>
          <Form.Item name="template_name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="如 颜色属性" />
          </Form.Item>
          <Form.Item name="template_level" label="模板级别" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '集团级', value: 'group' },
                { label: '企业级', value: 'enterprise' },
              ]}
            />
          </Form.Item>
          <Form.Item name="attribute_type" label="属性类型" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '文本', value: 'text' },
                { label: '数字', value: 'number' },
                { label: '枚举', value: 'enum' },
                { label: '日期', value: 'date' },
                { label: '布尔', value: 'boolean' },
              ]}
            />
          </Form.Item>
          <Form.Item name="is_required" label="是否必填" valuePropName="checked">
            <Checkbox>必填</Checkbox>
          </Form.Item>
          <Form.Item name="enum_values" label="枚举值(逗号分隔)">
            <Input placeholder="红,绿,蓝" />
          </Form.Item>
          <Form.Item name="min_value" label="最小值">
            <InputNumber placeholder="无限制" />
          </Form.Item>
          <Form.Item name="max_value" label="最大值">
            <InputNumber placeholder="无限制" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}