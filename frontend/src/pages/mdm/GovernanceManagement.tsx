import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, Select, Space, Tag, message, Tabs, Descriptions } from 'antd'
import { PlusOutlined, ReloadOutlined, CheckOutlined, CloseOutlined, RocketOutlined, RollbackOutlined } from '@ant-design/icons'
import { governanceApi } from '@/api/mdm'
import type { GovernanceRequest } from '@/api/mdm/types'

const { TextArea } = Input


const STATE_LABELS: Record<string, string> = {
  draft: '草稿',
  submitted: '已提交',
  approved: '已审批',
  published: '已发布',
  rejected: '已拒绝',
  rolled_back: '已回滚',
}
const STATE_COLORS: Record<string, string> = {
  draft: 'default',
  submitted: 'processing',
  approved: 'warning',
  published: 'success',
  rejected: 'error',
  rolled_back: 'error',
}

export default function GovernanceManagement() {
  const [groupRequests, setGroupRequests] = useState<GovernanceRequest[]>([])
  const [enterpriseRequests, setEnterpriseRequests] = useState<GovernanceRequest[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [actionModalOpen, setActionModalOpen] = useState(false)
  const [currentRequest, setCurrentRequest] = useState<GovernanceRequest | null>(null)
  const [actionType, setActionType] = useState<'approve' | 'reject' | 'publish' | 'rollback' | 'submit'>('approve')
  const [createForm] = Form.useForm()
  const [actionForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const [groupList, enterpriseList] = await Promise.all([
        governanceApi.listGroup(),
        governanceApi.listEnterprise(),
      ])
      setGroupRequests(groupList)
      setEnterpriseRequests(enterpriseList)
    } catch {
      message.error('加载治理工作流列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleCreate = async (level: 'group' | 'enterprise') => {
    const values = await createForm.validateFields()
    try {
      if (level === 'group') {
        await governanceApi.createGroup({
          entity_type: values.entity_type,
          entity_id: values.entity_id,
          governance_level: values.governance_level,
          tenant_id: values.tenant_id,
        })
      } else {
        await governanceApi.createEnterprise({
          entity_type: values.entity_type,
          entity_id: values.entity_id,
          governance_level: values.governance_level,
        })
      }
      message.success('变更申请创建成功')
      setCreateModalOpen(false)
      createForm.resetFields()
      loadData()
    } catch {
      message.error('创建失败')
    }
  }

  const handleAction = async () => {
    if (!currentRequest) return
    const values = await actionForm.validateFields().catch(() => ({ reason: '' }))
    try {
      const id = currentRequest.workflow_id
      switch (actionType) {
        case 'submit':
          await governanceApi.submit(id)
          break
        case 'approve':
          await governanceApi.approve(id, values.reason || '')
          break
        case 'reject':
          await governanceApi.reject(id, values.reason || '')
          break
        case 'publish':
          await governanceApi.publish(id)
          break
        case 'rollback':
          await governanceApi.rollback(id, values.reason || '')
          break
      }
      message.success('操作成功')
      setActionModalOpen(false)
      actionForm.resetFields()
      loadData()
    } catch {
      message.error('操作失败')
    }
  }

  const openAction = (req: GovernanceRequest, type: typeof actionType) => {
    setCurrentRequest(req)
    setActionType(type)
    setActionModalOpen(true)
  }

  const getActionButtons = (record: GovernanceRequest) => {
    const buttons: React.ReactNode[] = []
    if (record.state === 'draft') {
      buttons.push(
        <Button key="submit" size="small" type="primary" icon={<RocketOutlined />} onClick={() => openAction(record, 'submit')}>
          提交
        </Button>
      )
    }
    if (record.state === 'submitted') {
      buttons.push(
        <Button key="approve" size="small" type="primary" icon={<CheckOutlined />} onClick={() => openAction(record, 'approve')}>
          审批通过
        </Button>,
        <Button key="reject" size="small" danger icon={<CloseOutlined />} onClick={() => openAction(record, 'reject')}>
          拒绝
        </Button>
      )
    }
    if (record.state === 'approved') {
      buttons.push(
        <Button key="publish" size="small" type="primary" icon={<RocketOutlined />} onClick={() => openAction(record, 'publish')}>
          发布
        </Button>
      )
    }
    if (record.state === 'published') {
      buttons.push(
        <Button key="rollback" size="small" danger icon={<RollbackOutlined />} onClick={() => openAction(record, 'rollback')}>
          回滚
        </Button>
      )
    }
    return <Space size="small">{buttons}</Space>
  }

  const columns = [
    { title: '申请ID', dataIndex: 'workflow_id', key: 'workflow_id', render: (id: string) => id.substring(0, 8) + '...' },
    { title: '实体类型', dataIndex: 'entity_type', key: 'entity_type' },
    { title: '实体ID', dataIndex: 'entity_id', key: 'entity_id', render: (id: string | null) => id ? id.substring(0, 8) + '...' : '-' },
    {
      title: '治理级别',
      dataIndex: 'governance_level',
      key: 'governance_level',
      render: (level: string) => <Tag color={level === 'group' ? 'blue' : 'green'}>{level === 'group' ? '集团级' : '企业级'}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'state',
      key: 'state',
      render: (state: string) => <Tag color={STATE_COLORS[state] || 'default'}>{STATE_LABELS[state] || state}</Tag>,
    },
    { title: '当前版本', dataIndex: 'current_version', key: 'current_version' },
    { title: '目标版本', dataIndex: 'target_version', key: 'target_version' },
    { title: '操作', key: 'action', render: (_: unknown, record: GovernanceRequest) => getActionButtons(record) },
  ]

  const actionLabels: Record<string, string> = {
    submit: '提交',
    approve: '审批通过',
    reject: '拒绝',
    publish: '发布',
    rollback: '回滚',
  }

  return (
    <Card>
      <Tabs
        items={[
          {
            key: 'group',
            label: '集团级治理',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => { createForm.resetFields(); setCreateModalOpen(true) }}>
                    新建变更申请
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
                </Space>
                <Table columns={columns} dataSource={groupRequests} rowKey="workflow_id" loading={loading} pagination={{ pageSize: 20 }} />
              </>
            ),
          },
          {
            key: 'enterprise',
            label: '企业级治理',
            children: (
              <>
                <Space style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => { createForm.resetFields(); setCreateModalOpen(true) }}>
                    新建变更申请
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
                </Space>
                <Table columns={columns} dataSource={enterpriseRequests} rowKey="workflow_id" loading={loading} pagination={{ pageSize: 20 }} />
              </>
            ),
          },
        ]}
      />

      <Modal title="新建变更申请" open={createModalOpen} onCancel={() => setCreateModalOpen(false)} width={600}
        footer={[
          <Button key="cancel" onClick={() => setCreateModalOpen(false)}>取消</Button>,
          <Button key="group" type="primary" onClick={() => handleCreate('group')}>创建集团级</Button>,
          <Button key="enterprise" type="primary" onClick={() => handleCreate('enterprise')}>创建企业级</Button>,
        ]}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="entity_type" label="实体类型" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '集团商品', value: 'group_product' },
                { label: '企业商品', value: 'enterprise_product' },
                { label: '规格模板', value: 'spec_template' },
                { label: '属性模板', value: 'attribute_template' },
              ]}
            />
          </Form.Item>
          <Form.Item name="entity_id" label="实体ID" rules={[{ required: true }]}>
            <Input placeholder="实体 UUID" />
          </Form.Item>
          <Form.Item name="governance_level" label="治理级别" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '集团级', value: 'group' },
                { label: '企业级', value: 'enterprise' },
              ]}
            />
          </Form.Item>
          <Form.Item name="tenant_id" label="租户ID（企业级必填）">
            <Input placeholder="租户 UUID" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`${actionLabels[actionType]} - ${currentRequest?.workflow_id.substring(0, 8) || ''}...`}
        open={actionModalOpen}
        onOk={handleAction}
        onCancel={() => setActionModalOpen(false)}
      >
        {currentRequest && (
          <Descriptions size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="实体类型">{currentRequest.entity_type}</Descriptions.Item>
            <Descriptions.Item label="当前状态">{STATE_LABELS[currentRequest.state] || currentRequest.state}</Descriptions.Item>
            <Descriptions.Item label="当前版本">v{currentRequest.current_version}</Descriptions.Item>
            <Descriptions.Item label="目标版本">v{currentRequest.target_version}</Descriptions.Item>
          </Descriptions>
        )}
        {(actionType === 'approve' || actionType === 'reject' || actionType === 'rollback') && (
          <Form form={actionForm} layout="vertical">
            <Form.Item name="reason" label="原因说明" rules={[{ required: true }]}>
              <TextArea rows={3} placeholder="请说明原因" />
            </Form.Item>
          </Form>
        )}
      </Modal>
    </Card>
  )
}
