import { useState, useEffect } from 'react'
import { Card, Typography, Table, Button, Modal, Form, Select, Space, Tag, message, Progress, Alert } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { client } from '@/api/client'

const { Title, Paragraph } = Typography

interface PlacementInfo {
  tenant_id: string
  placement: string
  connection_target: string
  updated_at: string
}

interface MigrationStatus {
  task_id: string
  tenant_id: string
  phase: string
  progress_percent: number
  started_at: string
  completed_at: string | null
  failure_reason: string | null
}

const PLACEMENT_LABELS: Record<string, string> = {
  shared_db: '共享数据库',
  dedicated_db: '独立数据库',
  dedicated_instance: '独立实例',
}

const PHASE_LABELS: Record<string, string> = {
  pending: '等待中',
  freezing: '冻结写入',
  full_sync: '全量同步',
  incremental_sync: '增量同步',
  verifying: '数据校验',
  switching: '切换指向',
  completed: '已完成',
  failed: '失败',
  rolled_back: '已回滚',
}

export default function PlacementManagement() {
  const [placements, setPlacements] = useState<PlacementInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [migrateModalOpen, setMigrateModalOpen] = useState(false)
  const [migrationStatus] = useState<MigrationStatus | null>(null)
  const [form] = Form.useForm()
  const [migrateForm] = Form.useForm()

  const fetchPlacements = async () => {
    setLoading(true)
    try {
      const response = await client.get<PlacementInfo[]>('/platform/placement')
      setPlacements(response.data)
    } catch {
      message.error('加载放置列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPlacements()
  }, [])

  const handleSetPlacement = async () => {
    const values = await form.validateFields()
    try {
      await client.put(`/platform/placement/${values.tenant_id}`, {
        placement: values.placement,
      })
      message.success('放置模式设置成功')
      setModalOpen(false)
      form.resetFields()
      fetchPlacements()
    } catch {
      message.error('设置失败')
    }
  }

  const handleMigrate = async () => {
    const values = await migrateForm.validateFields()
    try {
      const response = await client.post<{ migration_task_id: string }>(
        `/platform/placement/${values.tenant_id}/migrate`,
        {
          target_placement: values.target_placement,
          maintenance_window: values.maintenance_window,
        },
      )
      message.success(`迁移任务已提交: ${response.data.migration_task_id}`)
      setMigrateModalOpen(false)
      migrateForm.resetFields()
    } catch {
      message.error('迁移发起失败')
    }
  }

  const columns: ColumnsType<PlacementInfo> = [
    { title: '租户 ID', dataIndex: 'tenant_id', key: 'tenant_id', ellipsis: true },
    {
      title: '放置模式',
      dataIndex: 'placement',
      key: 'placement',
      render: (placement: string) => (
        <Tag color={placement === 'shared_db' ? 'blue' : placement === 'dedicated_db' ? 'orange' : 'red'}>
          {PLACEMENT_LABELS[placement] || placement}
        </Tag>
      ),
    },
    { title: '连接目标', dataIndex: 'connection_target', key: 'connection_target', ellipsis: true },
    { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', ellipsis: true },
  ]

  return (
    <Card>
      <Title level={3}>平台运营 - 数据放置与迁移</Title>
      <Paragraph>
        管理租户数据放置模式：共享数据库 / 独立数据库 / 独立实例。支持在线迁移，迁移中冻结写入。
      </Paragraph>

      {migrationStatus && (
        <Alert
          type={migrationStatus.phase === 'completed' ? 'success' : 'info'}
          message={`迁移阶段: ${PHASE_LABELS[migrationStatus.phase] || migrationStatus.phase}`}
          description={<Progress percent={migrationStatus.progress_percent} />}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setModalOpen(true)}>设置放置模式</Button>
        <Button onClick={() => setMigrateModalOpen(true)}>发起迁移</Button>
        <Button onClick={fetchPlacements}>刷新</Button>
      </Space>

      <Table columns={columns} dataSource={placements} rowKey="tenant_id" loading={loading} />

      <Modal title="设置放置模式" open={modalOpen} onOk={handleSetPlacement} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="tenant_id" label="租户 ID" rules={[{ required: true }]}>
            <input style={{ width: '100%', padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }} />
          </Form.Item>
          <Form.Item name="placement" label="放置模式" rules={[{ required: true }]} initialValue="shared_db">
            <Select options={[
              { value: 'shared_db', label: '共享数据库' },
              { value: 'dedicated_db', label: '独立数据库' },
              { value: 'dedicated_instance', label: '独立实例' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="发起在线迁移" open={migrateModalOpen} onOk={handleMigrate} onCancel={() => setMigrateModalOpen(false)}>
        <Form form={migrateForm} layout="vertical">
          <Form.Item name="tenant_id" label="租户 ID" rules={[{ required: true }]}>
            <input style={{ width: '100%', padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }} />
          </Form.Item>
          <Form.Item name="target_placement" label="目标放置模式" rules={[{ required: true }]}>
            <Select options={[
              { value: 'dedicated_db', label: '独立数据库' },
              { value: 'dedicated_instance', label: '独立实例' },
            ]} />
          </Form.Item>
          <Form.Item name="maintenance_window" label="维护窗口" rules={[{ required: true }]}>
            <input
              style={{ width: '100%', padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }}
              placeholder="2026-01-01T02:00:00/2026-01-01T04:00:00"
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}