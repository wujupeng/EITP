import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Modal, Form, Input, Select } from 'antd'
import { pltApi } from '@/api/platform'

export default function PermissionMatrixPage() {
  const [entries, setEntries] = useState<any[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    pltApi.permission.matrix().then(resp => setEntries(resp.data.items || []))
  }, [])

  return (
    <Card title="权限矩阵管理" extra={<Button type="primary" onClick={() => setModalOpen(true)}>新增权限</Button>}>
      <Table dataSource={entries} rowKey="entry_id" columns={[
        { title: '角色', dataIndex: 'role_id' },
        { title: '操作', dataIndex: 'operation' },
        { title: '决策', dataIndex: 'decision', render: (v: string) => <Tag color={v === 'ALLOW' ? 'green' : 'red'}>{v}</Tag> },
        { title: '审批状态', dataIndex: 'approval_status', render: (v: string) => <Tag>{v}</Tag> },
        { title: '版本', dataIndex: 'version' },
      ]} />
      <Modal title="新增权限" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => { form.validateFields().then(v => { pltApi.permission.createEntry(v); setModalOpen(false) }) }}>
        <Form form={form} layout="vertical">
          <Form.Item name="role_id" label="角色 ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="operation" label="操作" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="decision" label="决策" rules={[{ required: true }]}><Select options={[{ label: '允许', value: 'ALLOW' }, { label: '拒绝', value: 'DENY' }]} /></Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}