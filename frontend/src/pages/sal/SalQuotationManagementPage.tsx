import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, message, Space, Tag, Steps } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { SalesQuotation } from '@/types/sal'

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', submitted: 'blue', approved: 'cyan',
  converted: 'green', rejected: 'red', expired: 'orange', cancelled: 'gray',
}

export default function SalQuotationManagementPage() {
  const [quotations, setQuotations] = useState<SalesQuotation[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [convertTarget, setConvertTarget] = useState<SalesQuotation | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.quotations.list()
      setQuotations(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.quotations.create(values)
      message.success('销售报价创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleAction = async (id: string, action: 'submit' | 'approve' | 'convert' | 'cancel') => {
    try {
      if (action === 'submit') await salApi.quotations.submit(id)
      else if (action === 'approve') await salApi.quotations.approve(id, { approved: true })
      else if (action === 'convert') await salApi.quotations.convert(id)
      else if (action === 'cancel') await salApi.quotations.cancel(id)
      message.success('操作成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '报价编码', dataIndex: 'quotation_code', key: 'quotation_code' },
    { title: '客户ID', dataIndex: 'customer_id', key: 'customer_id' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    { title: '有效期至', dataIndex: 'valid_until', key: 'valid_until' },
    { title: '转单订单', dataIndex: 'converted_order_id', key: 'converted_order_id' },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: SalesQuotation) => (
        <Space>
          {r.status === 'draft' && <Button size="small" type="link" onClick={() => handleAction(r.quotation_id, 'submit')}>提交</Button>}
          {r.status === 'submitted' && <Button size="small" type="link" onClick={() => handleAction(r.quotation_id, 'approve')}>审批</Button>}
          {r.status === 'approved' && (
            <Button size="small" type="link" onClick={() => setConvertTarget(r)}>转单</Button>
          )}
          {['draft', 'submitted'].includes(r.status) && <Button size="small" type="link" danger onClick={() => handleAction(r.quotation_id, 'cancel')}>取消</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建销售报价</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={quotations} rowKey="quotation_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建销售报价" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="quotation_code" label="报价编码" rules={[{ required: true }]}><Input placeholder="如 SQ001" /></Form.Item>
          <Form.Item name="customer_id" label="客户ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="valid_from" label="有效期起"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="valid_until" label="有效期止"><Input placeholder="YYYY-MM-DD" /></Form.Item>
          <Form.Item name="payment_terms" label="付款条款"><Input /></Form.Item>
          <Form.Item name="currency" label="币种" initialValue="CNY"><Input /></Form.Item>
        </Form>
      </Modal>
      <Modal
        title="报价转销售订单"
        open={!!convertTarget}
        onOk={() => { if (convertTarget) handleAction(convertTarget.quotation_id, 'convert'); setConvertTarget(null) }}
        onCancel={() => setConvertTarget(null)}
      >
        {convertTarget && (
          <div>
            <p>报价编码: {convertTarget.quotation_code}</p>
            <p>状态: <Tag color={STATUS_COLORS[convertTarget.status]}>{convertTarget.status}</Tag></p>
            <Steps
              size="small"
              current={2}
              items={[{ title: '审批' }, { title: '已批准' }, { title: '转单' }, { title: '生成订单' }]}
              style={{ marginTop: 16 }}
            />
          </div>
        )}
      </Modal>
    </div>
  )
}