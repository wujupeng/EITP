import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Tag, Drawer } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { Supplier } from '@/types/pur'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', submitted: 'blue', approved: 'cyan',
  active: 'green', disabled: 'red',
}

export default function PurSupplierManagementPage() {
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [current, setCurrent] = useState<Supplier | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.suppliers.list()
      setSuppliers(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.suppliers.create(values)
      message.success('供应商创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'approve' | 'publish' | 'disable') => {
    try {
      if (action === 'submit') await purApi.suppliers.submit(id)
      else if (action === 'approve') await purApi.suppliers.approve(id, { approved: true })
      else if (action === 'publish') await purApi.suppliers.publish(id)
      else if (action === 'disable') await purApi.suppliers.disable(id)
      message.success(`操作成功`)
      loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '供应商编码', dataIndex: 'supplier_code', key: 'supplier_code' },
    { title: '供应商名称', dataIndex: 'supplier_name', key: 'supplier_name' },
    { title: '类型', dataIndex: 'supplier_type', key: 'supplier_type' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, record: Supplier) => (
        <Space>
          <Button size="small" onClick={() => { setCurrent(record); setDrawerOpen(true) }}>详情</Button>
          {record.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(record.supplier_id, 'submit')}>提交</Button>}
          {record.status === 'submitted' && <Button size="small" type="link" onClick={() => handleAction(record.supplier_id, 'approve')}>审批</Button>}
          {record.status === 'approved' && <Button size="small" type="link" onClick={() => handleAction(record.supplier_id, 'publish')}>发布</Button>}
          {record.status === 'active' && <Button size="small" type="link" danger onClick={() => handleAction(record.supplier_id, 'disable')}>停用</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建供应商</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={suppliers} rowKey="supplier_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建供应商" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="supplier_code" label="供应商编码" rules={[{ required: true }]}><Input placeholder="如 SUP001" /></Form.Item>
          <Form.Item name="supplier_name" label="供应商名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="supplier_type" label="类型" initialValue="distributor">
            <Select options={[{ value: 'distributor', label: '经销商' }, { value: 'manufacturer', label: '制造商' }, { value: 'agent', label: '代理商' }]} />
          </Form.Item>
          <Form.Item name="contact_name" label="联系人"><Input /></Form.Item>
          <Form.Item name="contact_phone" label="联系电话"><Input /></Form.Item>
          <Form.Item name="contact_email" label="联系邮箱"><Input /></Form.Item>
        </Form>
      </Modal>
      <Drawer title="供应商详情" open={drawerOpen} onClose={() => setDrawerOpen(false)} width={500}>
        {current && (
          <div>
            <p>编码: {current.supplier_code}</p>
            <p>名称: {current.supplier_name}</p>
            <p>类型: {current.supplier_type}</p>
            <p>状态: <Tag color={STATUS_COLORS[current.status]}>{current.status}</Tag></p>
            <p>发布版本: {current.published_version}</p>
          </div>
        )}
      </Drawer>
    </div>
  )
}