import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, Select, message, Space, Tag, Steps } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { Disposition, QcResult, SalesReturn } from '@/types/sal'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', submitted: 'blue', approved: 'cyan',
  rejected: 'red', receiving: 'orange', qc: 'purple',
  disposed: 'magenta', completed: 'green', cancelled: 'gray',
}

const STATUS_FLOW = ['draft', 'submitted', 'approved', 'receiving', 'qc', 'disposed', 'completed']

export default function SalReturnManagementPage() {
  const [returns, setReturns] = useState<SalesReturn[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [qcOpen, setQcOpen] = useState(false)
  const [disposeOpen, setDisposeOpen] = useState(false)
  const [currentId, setCurrentId] = useState('')
  const [form] = Form.useForm()
  const [qcForm] = Form.useForm()
  const [disposeForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.returns.list()
      setReturns(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.returns.create(values)
      message.success('销售退货单创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'approve' | 'receive') => {
    try {
      if (action === 'submit') await salApi.returns.submit(id)
      else if (action === 'approve') await salApi.returns.approve(id, { approved: true })
      else if (action === 'receive') await salApi.returns.receive(id, { idempotency_key: crypto.randomUUID() })
      message.success('操作成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleQc = async () => {
    const values = await qcForm.validateFields()
    try {
      await salApi.returns.qc(currentId, values)
      message.success('QC 结论录入成功')
      setQcOpen(false); qcForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleDispose = async () => {
    const values = await disposeForm.validateFields()
    try {
      await salApi.returns.dispose(currentId, values)
      message.success('处置决策成功')
      setDisposeOpen(false); disposeForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '退货编码', dataIndex: 'return_code', key: 'return_code' },
    { title: '订单ID', dataIndex: 'order_id', key: 'order_id' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    { title: 'QC结论', dataIndex: 'qc_result', key: 'qc_result' },
    { title: '处置', dataIndex: 'disposition', key: 'disposition' },
    { title: 'WMS收货', dataIndex: 'wms_receiving_id', key: 'wms_receiving_id' },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: SalesReturn) => (
        <Space>
          {r.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(r.return_id, 'submit')}>提交</Button>}
          {r.status === 'submitted' && <Button size="small" type="link" onClick={() => handleAction(r.return_id, 'approve')}>审批</Button>}
          {r.status === 'approved' && <Button size="small" type="link" onClick={() => handleAction(r.return_id, 'receive')}>退货收货</Button>}
          {r.status === 'receiving' && (
            <Button size="small" type="link" onClick={() => { setCurrentId(r.return_id); setQcOpen(true) }}>QC录入</Button>
          )}
          {r.status === 'qc' && (
            <Button size="small" type="link" onClick={() => { setCurrentId(r.return_id); setDisposeOpen(true) }}>处置</Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建退货单</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={returns} rowKey="return_id" loading={loading} pagination={{ pageSize: 20 }}
        expandable={{
          expandedRowRender: (r) => (
            <Steps
              size="small"
              current={STATUS_FLOW.indexOf(r.status)}
              items={STATUS_FLOW.map((s) => ({ title: s }))}
            />
          ),
        }}
      />
      <Modal title="新建销售退货单" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="return_code" label="退货编码" rules={[{ required: true }]}><Input placeholder="如 SR001" /></Form.Item>
          <Form.Item name="order_id" label="销售订单ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="customer_id" label="客户ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="warehouse_id" label="仓库ID"><Input /></Form.Item>
        </Form>
      </Modal>
      <Modal title="QC 结论录入" open={qcOpen} onOk={handleQc} onCancel={() => setQcOpen(false)}>
        <Form form={qcForm} layout="vertical">
          <Form.Item name="line_id" label="退货行ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="qc_result" label="QC结论" rules={[{ required: true }]}>
            <Select options={[
              { value: 'passed' as QcResult, label: '合格' },
              { value: 'failed' as QcResult, label: '不合格' },
              { value: 'conditional' as QcResult, label: '条件合格' },
              { value: 'pending' as QcResult, label: '待定' },
            ]} />
          </Form.Item>
          <Form.Item name="qc_note" label="QC备注"><Input.TextArea /></Form.Item>
        </Form>
      </Modal>
      <Modal title="处置决策" open={disposeOpen} onOk={handleDispose} onCancel={() => setDisposeOpen(false)}>
        <Form form={disposeForm} layout="vertical">
          <Form.Item name="disposition" label="处置方式" rules={[{ required: true }]}>
            <Select options={[
              { value: 'restock' as Disposition, label: '重新入库' },
              { value: 'scrap' as Disposition, label: '报废' },
              { value: 'return_to_supplier' as Disposition, label: '退回供应商' },
              { value: 'rework' as Disposition, label: '返工' },
            ]} />
          </Form.Item>
          <Form.Item name="note" label="备注"><Input.TextArea /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}