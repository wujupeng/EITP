import { useState, useEffect } from 'react'
import { Card, Typography, Table, Button, Modal, Form, InputNumber, Space, Tag, message, Popconfirm } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { client } from '@/api/client'

const { Title, Paragraph } = Typography

interface BackupRecord {
  backup_id: string
  tenant_id: string
  backup_type: string
  storage_uri: string
  checksum: string
  status: string
  created_at: string
  expires_at: string
  size_bytes: number
  failure_reason: string | null
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'processing',
  in_progress: 'processing',
  completed: 'success',
  failed: 'error',
  expired: 'default',
}

const STATUS_LABELS: Record<string, string> = {
  pending: '等待中',
  in_progress: '备份中',
  completed: '已完成',
  failed: '失败',
  expired: '已过期',
}

export default function BackupManagement() {
  const [backups, setBackups] = useState<BackupRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [tenantId, setTenantId] = useState('')
  const [retentionModalOpen, setRetentionModalOpen] = useState(false)
  const [form] = Form.useForm()

  const fetchBackups = async () => {
    if (!tenantId) return
    setLoading(true)
    try {
      const response = await client.get<BackupRecord[]>(`/platform/backup/${tenantId}/list`)
      setBackups(response.data)
    } catch {
      message.error('加载备份列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (tenantId) fetchBackups()
  }, [tenantId])

  const handleTriggerBackup = async () => {
    if (!tenantId) return
    try {
      const response = await client.post<{ backup_id: string }>(`/platform/backup/${tenantId}`)
      message.success(`备份任务已提交: ${response.data.backup_id}`)
      fetchBackups()
    } catch {
      message.error('触发备份失败')
    }
  }

  const handleRestore = async (backupId: string) => {
    try {
      await client.post(`/platform/backup/${backupId}/restore`, {
        target_tenant_id: tenantId,
      })
      message.success('恢复任务已提交')
    } catch {
      message.error('恢复失败')
    }
  }

  const handleSetRetention = async () => {
    const values = await form.validateFields()
    try {
      await client.put(`/platform/backup/${tenantId}/retention`, {
        retain_days: values.retain_days,
        retain_copies: values.retain_copies,
      })
      message.success('保留策略设置成功')
      setRetentionModalOpen(false)
    } catch {
      message.error('设置失败')
    }
  }

  const columns: ColumnsType<BackupRecord> = [
    { title: '备份 ID', dataIndex: 'backup_id', key: 'backup_id', ellipsis: true },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] || 'default'}>{STATUS_LABELS[status] || status}</Tag>
      ),
    },
    { title: '类型', dataIndex: 'backup_type', key: 'backup_type' },
    { title: '校验值', dataIndex: 'checksum', key: 'checksum', ellipsis: true },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', ellipsis: true },
    { title: '过期时间', dataIndex: 'expires_at', key: 'expires_at', ellipsis: true },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Popconfirm
          title="确认恢复到此备份时点？"
          onConfirm={() => handleRestore(record.backup_id)}
          disabled={record.status !== 'completed'}
        >
          <Button size="small" disabled={record.status !== 'completed'}>恢复</Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <Card>
      <Title level={3}>平台运营 - 备份与恢复</Title>
      <Paragraph>
        租户级独立备份，备份不影响其他租户。支持触发备份、恢复至备份时点、配置保留策略。
        跨租户恢复被拒绝（C-BACKUP-01）。
      </Paragraph>

      <Space style={{ marginBottom: 16 }}>
        <input
          style={{ width: 300, padding: '4px 11px', border: '1px solid #d9d9d9', borderRadius: 6 }}
          placeholder="输入租户 ID"
          value={tenantId}
          onChange={(e) => setTenantId(e.target.value)}
        />
        <Button type="primary" onClick={handleTriggerBackup} disabled={!tenantId}>触发备份</Button>
        <Button onClick={() => setRetentionModalOpen(true)} disabled={!tenantId}>保留策略</Button>
        <Button onClick={fetchBackups} disabled={!tenantId}>刷新</Button>
      </Space>

      <Table columns={columns} dataSource={backups} rowKey="backup_id" loading={loading} />

      <Modal title="配置保留策略" open={retentionModalOpen} onOk={handleSetRetention} onCancel={() => setRetentionModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="retain_days" label="保留天数" initialValue={30} rules={[{ required: true }]}>
            <InputNumber min={1} max={3650} />
          </Form.Item>
          <Form.Item name="retain_copies" label="保留份数" initialValue={10} rules={[{ required: true }]}>
            <InputNumber min={1} max={100} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}