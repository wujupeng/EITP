import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, Select, Space, Tag, message, Tabs, Divider, Checkbox } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { specTemplateApi } from '@/api/mdm'
import type { SpecTemplate, AttributeDefinition } from '@/api/mdm/types'

export default function SpecTemplateManagement() {
  const [groupTemplates, setGroupTemplates] = useState<SpecTemplate[]>([])
  const [enterpriseTemplates, setEnterpriseTemplates] = useState<SpecTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [groupList, enterpriseList] = await Promise.all([
        specTemplateApi.listGroup(),
        specTemplateApi.listEnterprise(),
      ])
      setGroupTemplates(groupList)
      setEnterpriseTemplates(enterpriseList)
    } catch {
      message.error('加载规格模板列表失败')
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
      const attribute_definitions: AttributeDefinition[] = values.attribute_definitions || []
      await specTemplateApi.create({
        template_code: values.template_code,
        template_name: values.template_name,
        template_level: values.template_level,
        attribute_definitions,
      })
      message.success('规格模板创建成功')
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
      title: '属性数量',
      key: 'attr_count',
      render: (_: unknown, record: SpecTemplate) => record.attribute_definitions?.length || 0,
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
            label: '集团级规格模板',
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
            label: '企业级规格模板',
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

      <Modal title="新建规格模板" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={700}>
        <Form form={form} layout="vertical">
          <Form.Item name="template_code" label="模板编码" rules={[{ required: true }]}>
            <Input placeholder="如 SPEC-001" />
          </Form.Item>
          <Form.Item name="template_name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="如 电子产品规格" />
          </Form.Item>
          <Form.Item name="template_level" label="模板级别" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '集团级', value: 'group' },
                { label: '企业级', value: 'enterprise' },
              ]}
            />
          </Form.Item>
          <Divider>属性定义</Divider>
          <Form.List name="attribute_definitions">
            {(fields, { add, remove }) => (
              <>
                {fields.map((field) => (
                  <Space key={field.key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                    <Form.Item name={[field.name, 'attribute_name']} rules={[{ required: true }]}>
                      <Input placeholder="属性名" />
                    </Form.Item>
                    <Form.Item name={[field.name, 'attribute_type']} rules={[{ required: true }]}>
                      <Select
                        style={{ width: 120 }}
                        placeholder="类型"
                        options={[
                          { label: '文本', value: 'text' },
                          { label: '数字', value: 'number' },
                          { label: '枚举', value: 'enum' },
                          { label: '日期', value: 'date' },
                          { label: '布尔', value: 'boolean' },
                        ]}
                      />
                    </Form.Item>
                    <Form.Item name={[field.name, 'is_required']} valuePropName="checked">
                      <Checkbox>必填</Checkbox>
                    </Form.Item>
                    <Button danger onClick={() => remove(field.name)}>删除</Button>
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                  添加属性
                </Button>
              </>
            )}
          </Form.List>
        </Form>
      </Modal>
    </Card>
  )
}
