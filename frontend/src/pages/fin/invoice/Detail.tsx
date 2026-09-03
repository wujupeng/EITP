import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Table, Button, Space, message } from 'antd'
import { invoiceApi } from '@/api/fin/invoice'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [invoice, setInvoice] = useState<any>(null)

  useEffect(() => {
    if (id) invoiceApi.get(id).then(resp => setInvoice(resp.data))
  }, [id])

  const handleVerify = async () => {
    try {
      await invoiceApi.verify(id!)
      message.success('发票验真成功')
      const resp = await invoiceApi.get(id!)
      setInvoice(resp.data)
    } catch {
      message.error('发票验真失败')
    }
  }

  const handleArchive = async () => {
    try {
      await invoiceApi.archive(id!)
      message.success('发票归档成功')
      const resp = await invoiceApi.get(id!)
      setInvoice(resp.data)
    } catch {
      message.error('发票归档失败')
    }
  }

  if (!invoice) return <Card title="发票详情">加载中...</Card>

  const lineColumns = [
    { title: '货物名称', dataIndex: 'item_name', key: 'item_name' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '单价', dataIndex: 'unit_price', key: 'unit_price', render: (v: string) => formatMoney(v, invoice.currency) },
    { title: '金额', dataIndex: 'line_amount', key: 'line_amount', render: (v: string) => formatMoney(v, invoice.currency) },
    { title: '税率', dataIndex: 'tax_rate', key: 'tax_rate' },
  ]

  return (
    <Card title={`发票详情 - ${invoice.invoice_number}`} extra={<Button onClick={() => navigate('/fin/invoices')}>返回</Button>}>
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="发票号">{invoice.invoice_number}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{invoice.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="购方">{invoice.buyer}</Descriptions.Item>
        <Descriptions.Item label="销方">{invoice.seller}</Descriptions.Item>
        <Descriptions.Item label="金额">{formatMoney(invoice.amount, invoice.currency)}</Descriptions.Item>
        <Descriptions.Item label="税额">{formatMoney(invoice.tax_amount, invoice.currency)}</Descriptions.Item>
        <Descriptions.Item label="价税合计">{formatMoney(invoice.total_amount, invoice.currency)}</Descriptions.Item>
        <Descriptions.Item label="开票日期">{invoice.issued_at}</Descriptions.Item>
      </Descriptions>
      <Table columns={lineColumns} dataSource={invoice.lines || []} rowKey="item_name" pagination={false} style={{ marginBottom: 16 }} />
      <Space>
        <Button type="primary" onClick={handleVerify}>验真</Button>
        <Button onClick={handleArchive}>归档</Button>
      </Space>
    </Card>
  )
}