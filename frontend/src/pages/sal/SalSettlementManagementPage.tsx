import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, Select, message, Space, Tag, Steps } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { PaymentMethod, SalesSettlement } from '@/types/sal'

const STATUS_COLORS: Record<string, string> = {
  pending: 'default', reconciled: 'blue', diff_found: 'red',
  invoice_matched: 'cyan', payment_requested: 'orange',
  payment_completed: 'green', failed: 'volcano',
}

const STATUS_FLOW = ['pending', 'reconciled', 'invoice_matched', 'payment_requested', 'payment_completed']

export default function SalSettlementManagementPage() {
  const [settlements, setSettlements] = useState<SalesSettlement[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [reconcileOpen, setReconcileOpen] = useState(false)
  const [matchOpen, setMatchOpen] = useState(false)
  const [payOpen, setPayOpen] = useState(false)
  const [currentId, setCurrentId] = useState('')
  const [form] = Form.useForm()
  const [reconcileForm] = Form.useForm()
  const [matchForm] = Form.useForm()
  const [payForm] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.settlements.list()
      setSettlements(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await salApi.settlements.create(values)
      message.success('结算单创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleReconcile = async () => {
    const values = await reconcileForm.validateFields()
    try {
      await salApi.settlements.reconcile(currentId, { ...values, idempotency_key: crypto.randomUUID() })
      message.success('对账成功（已通过 INV Financial/Revenue API 落地收入）')
      setReconcileOpen(false); reconcileForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handleMatch = async () => {
    const values = await matchForm.validateFields()
    try {
      await salApi.settlements.matchInvoice(currentId, values)
      message.success('发票匹配成功'); setMatchOpen(false); matchForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const handlePay = async () => {
    const values = await payForm.validateFields()
    try {
      await salApi.settlements.requestPayment(currentId, values)
      message.success('收款申请提交成功'); setPayOpen(false); payForm.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '结算编码', dataIndex: 'settlement_code', key: 'settlement_code' },
    { title: '订单ID', dataIndex: 'order_id', key: 'order_id' },
    { title: '总金额', dataIndex: 'total_amount', key: 'total_amount' },
    { title: '已发金额', dataIndex: 'shipped_amount', key: 'shipped_amount' },
    { title: '差异', dataIndex: 'diff_amount', key: 'diff_amount' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '收入落地', dataIndex: 'revenue_landed', key: 'revenue_landed',
      render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '已落地' : '未落地'}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: SalesSettlement) => (
        <Space>
          {r.status === 'pending' && (
            <Button size="small" type="primary" onClick={() => { setCurrentId(r.settlement_id); setReconcileOpen(true) }}>对账</Button>
          )}
          {r.status === 'reconciled' && (
            <Button size="small" type="link" onClick={() => { setCurrentId(r.settlement_id); setMatchOpen(true) }}>匹配发票</Button>
          )}
          {r.status === 'invoice_matched' && (
            <Button size="small" type="link" onClick={() => { setCurrentId(r.settlement_id); setPayOpen(true) }}>申请收款</Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建结算单</Button>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={settlements} rowKey="settlement_id" loading={loading} pagination={{ pageSize: 20 }}
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
      <Modal title="新建结算单" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} width={600}>
        <Form form={form} layout="vertical">
          <Form.Item name="settlement_code" label="结算编码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="order_id" label="订单ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="customer_id" label="客户ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="total_amount" label="总金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
      <Modal title="对账确认（通过 INV Financial/Revenue API 落地收入）" open={reconcileOpen} onOk={handleReconcile} onCancel={() => setReconcileOpen(false)}>
        <Form form={reconcileForm} layout="vertical">
          <Form.Item name="shipped_amount" label="实际发货金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
      <Modal title="匹配发票" open={matchOpen} onOk={handleMatch} onCancel={() => setMatchOpen(false)}>
        <Form form={matchForm} layout="vertical">
          <Form.Item name="invoice_id" label="发票ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="matched_amount" label="匹配金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
        </Form>
      </Modal>
      <Modal title="申请收款" open={payOpen} onOk={handlePay} onCancel={() => setPayOpen(false)}>
        <Form form={payForm} layout="vertical">
          <Form.Item name="payment_code" label="收款编码" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="amount" label="金额" rules={[{ required: true }]}><InputNumber min={0} /></Form.Item>
          <Form.Item name="payment_method" label="收款方式" rules={[{ required: true }]} initialValue="bank_transfer">
            <Select options={[
              { value: 'bank_transfer' as PaymentMethod, label: '银行转账' },
              { value: 'cheque' as PaymentMethod, label: '支票' },
              { value: 'cash' as PaymentMethod, label: '现金' },
              { value: 'credit_card' as PaymentMethod, label: '信用卡' },
              { value: 'electronic' as PaymentMethod, label: '电子支付' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}