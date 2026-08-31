import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { PurchaseRequest } from '@/types/pur'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', submitted: 'blue', approved: 'green',
  rejected: 'red', converted: 'purple', cancelled: 'orange',
}

export default function PurRequestManagementPage() {
  const [requests, setRequests] = useState<PurchaseRequest[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.requests.list()
      setRequests(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.requests.create(values)
      message.success('采购申请创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'approve' | 'convert' | 'cancel') => {
    try {
      if (action === 'submit') await purApi.requests.submit(id)
      else if (action === 'approve') await purApi.requests.approve(id, { approved: true })
      else if (action === 'convert') await purApi.requests.convert(id)
      else if (action === 'cancel') await purApi.requests.cancel(id)
      message.success('操作成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '申请编码', dataIndex: 'request_code', key: 'request_code' },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '总金额', dataIndex: 'total_amount', key: 'total_amount' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> },
    { title: '操作', key: 'action',
      render: (_: unknown, r: PurchaseRequest) => (
        <Space>
          {r.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(r.request_id, 'submit')}>提交</Button>}
          {r.status === 'submitted' && <Button size="small" type="link" onClick={() => handleAction(r.request_id, 'approve')}>审批</Button>}
          {r.status === 'approved' && <Button size="small" type="link" onClick={() => handleAction(r.request_id, 'convert')}>转单</Button>}
          {['draft', 'submitted'].includes(r.status) && <Button size="small" type="link" danger onClick={() => handleAction(r.request_id, 'cancel')}>取消</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建采购申请</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={requests} rowKey="request_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建采购申请" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="request_code" label="申请编码" rules={[{ required: true }]}><Input placeholder="如 PR001" /></Form.Item>
          <Form.Item name="title" label="标题"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}