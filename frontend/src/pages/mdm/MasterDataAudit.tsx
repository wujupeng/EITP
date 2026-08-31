import { useState } from 'react'
import { Card, Table, Form, Input, Select, Button, Space, Tag, message, Typography } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { masterDataAuditApi } from '@/api/mdm'
import type { MasterDataAudit } from '@/api/mdm/types'

const { Text } = Typography

const ACTION_COLORS: Record<string, string> = {
  create: 'green',
  update: 'blue',
  delete: 'red',
  publish: 'purple',
  rollback: 'orange',
  approve: 'cyan',
  reject: 'red',
  submit: 'gold',
}

export default function MasterDataAudit() {
  const [auditLogs, setAuditLogs] = useState<MasterDataAudit[]>([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const handleSearch = async () => {
    const values = await form.validateFields().catch(() => ({}))
    setLoading(true)
    try {
      const params: {
        entity_type?: string
        entity_id?: string
        action?: string
        limit?: number
        offset?: number
      } = {}
      if (values.entity_type) params.entity_type = values.entity_type
      if (values.entity_id) params.entity_id = values.entity_id
      if (values.action) params.action = values.action
      params.limit = values.limit || 50
      params.offset = 0
      const data = await masterDataAuditApi.list(params)
      setAuditLogs(data)
    } catch {
      message.error('查询审计日志失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '审计ID',
      dataIndex: 'audit_id',
      key: 'audit_id',
      render: (id: string) => <Text type="secondary">{id.substring(0, 8)}...</Text>,
    },
    {
      title: '操作类型',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => <Tag color={ACTION_COLORS[action] || 'default'}>{action}</Tag>,
    },
    { title: '实体类型', dataIndex: 'entity_type', key: 'entity_type' },
    {
      title: '实体ID',
      dataIndex: 'entity_id',
      key: 'entity_id',
      render: (id: string) => <Text type="secondary">{id.substring(0, 8)}...</Text>,
    },
    {
      title: '版本',
      dataIndex: 'version_number',
      key: 'version_number',
      render: (v: number | null) => v ? <Tag color="blue">v{v}</Tag> : '-',
    },
    {
      title: '操作人',
      dataIndex: 'operated_by',
      key: 'operated_by',
      render: (id: string | null) => id ? <Text type="secondary">{id.substring(0, 8)}...</Text> : '-',
    },
    { title: '操作时间', dataIndex: 'operated_at', key: 'operated_at' },
    { title: '原因', dataIndex: 'reason', key: 'reason', render: (r: string | null) => r || '-' },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      render: (ip: string | null) => ip || '-',
    },
  ]

  return (
    <Card>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="entity_type" label="实体类型">
          <Select
            allowClear
            style={{ width: 150 }}
            options={[
              { label: '集团商品', value: 'group_product' },
              { label: '企业商品', value: 'enterprise_product' },
              { label: '规格模板', value: 'spec_template' },
              { label: '属性模板', value: 'attribute_template' },
              { label: '集团分类', value: 'group_category' },
              { label: '集团品牌', value: 'group_brand' },
              { label: '集团单位', value: 'group_unit' },
            ]}
          />
        </Form.Item>
        <Form.Item name="entity_id" label="实体ID">
          <Input placeholder="实体 UUID" style={{ width: 250 }} />
        </Form.Item>
        <Form.Item name="action" label="操作类型">
          <Select
            allowClear
            style={{ width: 120 }}
            options={[
              { label: '创建', value: 'create' },
              { label: '更新', value: 'update' },
              { label: '删除', value: 'delete' },
              { label: '发布', value: 'publish' },
              { label: '回滚', value: 'rollback' },
              { label: '提交', value: 'submit' },
              { label: '审批', value: 'approve' },
              { label: '拒绝', value: 'reject' },
            ]}
          />
        </Form.Item>
        <Form.Item name="limit" label="限制">
          <Input placeholder="50" style={{ width: 80 }} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleSearch}>
              查询
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => { form.resetFields(); setAuditLogs([]) }}>
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Table
        columns={columns}
        dataSource={auditLogs}
        rowKey="audit_id"
        loading={loading}
        pagination={{ pageSize: 20 }}
        scroll={{ x: 1200 }}
      />
    </Card>
  )
}
