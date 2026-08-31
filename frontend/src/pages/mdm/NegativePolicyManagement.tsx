import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Select, Space, Tag, message, Descriptions, Input, Alert, Typography } from 'antd'
import { ReloadOutlined, EditOutlined } from '@ant-design/icons'
import { negativePolicyApi } from '@/api/mdm'
import type { NegativePolicyConfig, NegativePolicyAudit } from '@/api/mdm/types'

const { Text } = Typography

const POLICY_LABELS: Record<string, string> = {
  strict: '严格禁止',
  allow: '允许',
  warning: '警告',
  approval: '需审批',
}
const POLICY_COLORS: Record<string, string> = {
  strict: 'red',
  allow: 'green',
  warning: 'orange',
  approval: 'blue',
}

export default function NegativePolicyManagement() {
  const [config, setConfig] = useState<NegativePolicyConfig | null>(null)
  const [auditHistory, setAuditHistory] = useState<NegativePolicyAudit[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [cfg, history] = await Promise.all([
        negativePolicyApi.get(),
        negativePolicyApi.listAudit(),
      ])
      setConfig(cfg)
      setAuditHistory(history)
    } catch {
      message.error('加载负库存策略失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleChange = async () => {
    const values = await form.validateFields()
    try {
      await negativePolicyApi.change({
        policy_mode: values.policy_mode,
        reason: values.reason,
      })
      message.success('策略变更成功')
      setModalOpen(false)
      form.resetFields()
      loadData()
    } catch {
      message.error('策略变更失败')
    }
  }

  const auditColumns = [
    {
      title: '审计ID',
      dataIndex: 'audit_id',
      key: 'audit_id',
      render: (id: string) => id.substring(0, 8) + '...',
    },
    {
      title: '变更前策略',
      dataIndex: 'policy_before',
      key: 'policy_before',
      render: (p: string) => <Tag color={POLICY_COLORS[p]}>{POLICY_LABELS[p] || p}</Tag>,
    },
    {
      title: '变更后策略',
      dataIndex: 'policy_after',
      key: 'policy_after',
      render: (p: string) => <Tag color={POLICY_COLORS[p]}>{POLICY_LABELS[p] || p}</Tag>,
    },
    {
      title: '操作人',
      dataIndex: 'operated_by',
      key: 'operated_by',
      render: (id: string) => id.substring(0, 8) + '...',
    },
    { title: '操作时间', dataIndex: 'operated_at', key: 'operated_at' },
    { title: '原因', dataIndex: 'reason', key: 'reason' },
  ]

  return (
    <Card loading={loading}>
      <Descriptions title="当前负库存策略" bordered column={2} style={{ marginBottom: 24 }}>
        <Descriptions.Item label="租户ID">
          {config?.tenant_id ? config.tenant_id.substring(0, 8) + '...' : '-'}
        </Descriptions.Item>
        <Descriptions.Item label="当前策略">
          {config && (
            <Tag color={POLICY_COLORS[config.policy_mode]} style={{ fontSize: 14 }}>
              {POLICY_LABELS[config.policy_mode] || config.policy_mode}
            </Tag>
          )}
        </Descriptions.Item>
      </Descriptions>

      {config?.policy_mode !== 'strict' && (
        <Alert
          type="warning"
          message="当前策略非严格模式"
          description="允许负库存可能导致库存数据不一致，建议在生产环境中使用 STRICT 模式。"
          style={{ marginBottom: 16 }}
          showIcon
        />
      )}

      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<EditOutlined />} onClick={() => setModalOpen(true)}>
          变更策略
        </Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>
          刷新
        </Button>
      </Space>

      <Text strong style={{ display: 'block', marginBottom: 8 }}>策略变更审计历史</Text>
      <Table
        columns={auditColumns}
        dataSource={auditHistory}
        rowKey="audit_id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title="变更负库存策略"
        open={modalOpen}
        onOk={handleChange}
        onCancel={() => setModalOpen(false)}
      >
        <Alert
          type="info"
          message="策略变更将记录审计日志，变更原因必填。"
          style={{ marginBottom: 16 }}
          showIcon
        />
        <Form form={form} layout="vertical">
          <Form.Item name="policy_mode" label="新策略" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '严格禁止（STRICT）- 禁止任何负库存操作', value: 'strict' },
                { label: '允许（ALLOW）- 允许负库存操作', value: 'allow' },
                { label: '警告（WARNING）- 允许但记录警告', value: 'warning' },
                { label: '需审批（APPROVAL）- 需要审批才能执行', value: 'approval' },
              ]}
            />
          </Form.Item>
          <Form.Item name="reason" label="变更原因" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="请详细说明变更原因" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
