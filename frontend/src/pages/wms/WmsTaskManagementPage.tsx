import { useState, useEffect } from 'react'
import { Card, Table, Button, Modal, Form, Input, Space, Tag, message, Timeline, Drawer, Radio } from 'antd'
import { ReloadOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { wmsApi } from '@/api/wms'
import { useWmsStore } from '@/store/wms'
import type { WmsTask, WmsTaskStatus } from '@/types/wms'

const statusColorMap: Record<WmsTaskStatus, string> = {
  created: 'default', assigned: 'blue', in_progress: 'processing', completed: 'green', cancelled: 'red', failed: 'error',
}

const priorityColorMap: Record<string, string> = { high: 'red', medium: 'orange', low: 'default' }

export default function WmsTaskManagementPage() {
  const { tasks, tasksLoading, loadTasks, startTaskPolling, stopTaskPolling, setExecuting } = useWmsStore()
  const [filterStatus, setFilterStatus] = useState<WmsTaskStatus | undefined>(undefined)
  const [polling, setPolling] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)
  const [currentTask, setCurrentTask] = useState<WmsTask | null>(null)
  const [traceOpen, setTraceOpen] = useState(false)
  const [traceTask, setTraceTask] = useState<WmsTask | null>(null)
  const [assignForm] = Form.useForm()

  useEffect(() => {
    loadTasks({ status: filterStatus })
    return () => stopTaskPolling()
  }, [filterStatus])

  const togglePolling = () => {
    if (polling) {
      stopTaskPolling()
      setPolling(false)
    } else {
      startTaskPolling({ status: filterStatus })
      setPolling(true)
    }
  }

  const handleAssign = async () => {
    if (!currentTask) return
    const values = await assignForm.validateFields()
    setExecuting(true)
    try {
      await wmsApi.tasks.assign(currentTask.task_id, { assignee_id: values.assignee_id })
      message.success('分配成功')
      setAssignOpen(false)
      assignForm.resetFields()
      loadTasks({ status: filterStatus })
    } catch {
      message.error('分配失败')
    } finally {
      setExecuting(false)
    }
  }

  const handleClaim = async (taskId: string) => {
    setExecuting(true)
    try {
      await wmsApi.tasks.claim(taskId)
      message.success('领取成功')
      loadTasks({ status: filterStatus })
    } catch {
      message.error('领取失败')
    } finally {
      setExecuting(false)
    }
  }

  const handleCancel = async (taskId: string) => {
    setExecuting(true)
    try {
      await wmsApi.tasks.cancel(taskId)
      message.success('取消成功')
      loadTasks({ status: filterStatus })
    } catch {
      message.error('取消失败')
    } finally {
      setExecuting(false)
    }
  }

  const columns = [
    { title: 'Task ID', dataIndex: 'task_id', key: 'task_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '类型', dataIndex: 'task_type', key: 'task_type', render: (v: string) => <Tag>{v}</Tag> },
    { title: '单据类型', dataIndex: 'document_type', key: 'document_type' },
    { title: '单据 ID', dataIndex: 'document_id', key: 'document_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '优先级', dataIndex: 'priority', key: 'priority', render: (v: string) => <Tag color={priorityColorMap[v]}>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: WmsTaskStatus) => <Tag color={statusColorMap[v]}>{v}</Tag> },
    { title: '分配人', dataIndex: 'assignee_id', key: 'assignee_id', render: (v: string | null) => v ? v.substring(0, 8) + '...' : '-' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: WmsTask) => (
        <Space size="small">
          {record.status === 'created' && (
            <Button size="small" type="primary" onClick={() => { setCurrentTask(record); setAssignOpen(true) }}>分配</Button>
          )}
          {record.status === 'assigned' && (
            <Button size="small" type="primary" onClick={() => handleClaim(record.task_id)}>领取</Button>
          )}
          {(record.status === 'created' || record.status === 'assigned') && (
            <Button size="small" danger onClick={() => handleCancel(record.task_id)}>取消</Button>
          )}
          <Button size="small" icon={<PlayCircleOutlined />} onClick={() => { setTraceTask(record); setTraceOpen(true) }}>链路</Button>
        </Space>
      ),
    },
  ]

  const traceItems = traceTask ? [
    { color: 'green', children: `创建于 ${traceTask.created_at || '-'}` },
    traceTask.assigned_at && { color: 'blue', children: `分配于 ${traceTask.assigned_at}` },
    traceTask.started_at && { color: 'blue', children: `开始于 ${traceTask.started_at}` },
    traceTask.completed_at && { color: 'green', children: `完成于 ${traceTask.completed_at}` },
    traceTask.inv_transaction_ids.length > 0 && { color: 'purple', children: `INV 事务: ${traceTask.inv_transaction_ids.map((id) => id.substring(0, 8) + '...').join(', ')}` },
  ].filter(Boolean) as { color: string; children: string }[] : []

  return (
    <Card title="WMS Task 管理">
      <Space style={{ marginBottom: 16 }}>
        <Radio.Group
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          options={[
            { label: '全部', value: undefined },
            { label: '待领取', value: 'assigned' as WmsTaskStatus },
            { label: '进行中', value: 'in_progress' as WmsTaskStatus },
            { label: '已完成', value: 'completed' as WmsTaskStatus },
          ]}
        />
        <Button icon={<ReloadOutlined />} onClick={() => loadTasks({ status: filterStatus })}>刷新</Button>
        <Button type={polling ? 'default' : 'primary'} onClick={togglePolling}>
          {polling ? '停止轮询' : '开启轮询(5s)'}
        </Button>
        {polling && <Tag color="processing">轮询中</Tag>}
      </Space>

      <Table columns={columns} dataSource={tasks} rowKey="task_id" loading={tasksLoading} pagination={{ pageSize: 20 }} />

      <Modal title="分配任务" open={assignOpen} onOk={handleAssign} onCancel={() => setAssignOpen(false)}>
        <Form form={assignForm} layout="vertical">
          <Form.Item name="assignee_id" label="分配给（用户 ID）" rules={[{ required: true }]}>
            <Input placeholder="用户 ID" />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer title="执行链路" open={traceOpen} onClose={() => setTraceOpen(false)} width={400}>
        {traceTask && (
          <>
            <Space direction="vertical" style={{ marginBottom: 16 }}>
              <Tag color={statusColorMap[traceTask.status]}>{traceTask.status}</Tag>
              <span>类型: {traceTask.task_type}</span>
              <span>单据: {traceTask.document_type} - {traceTask.document_id.substring(0, 8)}...</span>
            </Space>
            <Timeline items={traceItems} />
          </>
        )}
      </Drawer>
    </Card>
  )
}
