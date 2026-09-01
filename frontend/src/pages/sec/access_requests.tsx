import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Modal, Form, Input, Space, message } from 'antd'
import { secApi } from '@/api/sec'

export default function SecAccessRequestsPage() {
  const [requests, setRequests] = useState<any[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const load = () => secApi.listAccessRequests().then(resp => setRequests(resp.data.requests || []))
  useEffect(() => { load() }, [])

  const handleSubmit = async () => {
    const values = await form.validateFields()
    try {
      await secApi.submitAccessRequest(values)
      message.success('申请已提交')
      setModalOpen(false)
      load()
    } catch { message.error('提交失败') }
  }

  const handleApprove = async (id: string) => {
    try { await secApi.approveAccessRequest(id); message.success('已审批'); load() } catch { message.error('审批失败') }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Card title="平台管理员访问申请" extra={<Button type="primary" onClick={() => setModalOpen(true)}>提交申请</Button>}>
        <Table dataSource={requests} rowKey="request_id" columns={[
          { title: '申请ID', dataIndex: 'request_id' },
          { title: '目标租户', dataIndex: 'target_tenant_id' },
          { title: '数据范围', dataIndex: 'target_data_scope' },
          { title: '状态', dataIndex: 'approval_status', render: (v: string) => <Tag color={v === 'granted' ? 'green' : v === 'rejected' ? 'red' : 'orange'}>{v}</Tag> },
          { title: '操作', render: (_, r) => r.approval_status === 'pending' ? <Button size="small" type="link" onClick={() => handleApprove(r.request_id)}>审批</Button> : null },
        ]} />
      </Card>
      <Modal title="提交访问申请" open={modalOpen} onOk={handleSubmit} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="target_tenant_id" label="目标租户ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="target_data_scope" label="数据范围" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="reason" label="申请原因" rules={[{ required: true }]}><Input.TextArea /></Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}