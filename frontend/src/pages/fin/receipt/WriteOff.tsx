import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Form, Input, Button, message, Table } from 'antd'
import { receiptApi } from '@/api/fin/receipt'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function ReceiptWriteOffPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [receipt, setReceipt] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    if (id) receiptApi.get(id).then(resp => setReceipt(resp.data))
  }, [id])

  const handleWriteOff = async () => {
    setLoading(true)
    try {
      const values = await form.validateFields()
      await receiptApi.writeOff(id!, values)
      message.success('收款核销成功')
      navigate(`/fin/receipts/${id}`)
    } catch {
      message.error('收款核销失败')
    } finally {
      setLoading(false)
    }
  }

  if (!receipt) return <Card title="收款核销">加载中...</Card>

  return (
    <Card title="收款核销">
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="收款编号">{receipt.receipt_number}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{receipt.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="金额">{formatMoney(receipt.amount, receipt.currency)}</Descriptions.Item>
        <Descriptions.Item label="付款方">{receipt.payer}</Descriptions.Item>
      </Descriptions>
      <Table
        style={{ marginBottom: 16 }}
        columns={[
          { title: '应收单据', dataIndex: 'ref_doc', key: 'ref_doc' },
          { title: '应收金额', dataIndex: 'receivable_amount', key: 'receivable_amount', render: (v: string) => formatMoney(v, receipt.currency) },
          { title: '未核销', dataIndex: 'remaining', key: 'remaining', render: (v: string) => formatMoney(v, receipt.currency) },
        ]}
        dataSource={receipt.receivables || []}
        rowKey="ref_doc"
        pagination={false}
      />
      <Form form={form} layout="vertical" style={{ maxWidth: 600 }}>
        <Form.Item name="ref_doc" label="核销单据" rules={[{ required: true }]}>
          <Input placeholder="应收单据编号" />
        </Form.Item>
        <Form.Item name="write_off_amount" label="核销金额" rules={[{ required: true }]}>
          <Input placeholder="0.00" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" loading={loading} onClick={handleWriteOff}>执行核销</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}