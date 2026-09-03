import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Table, Button } from 'antd'
import { receiptApi } from '@/api/fin/receipt'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function ReceiptDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [receipt, setReceipt] = useState<any>(null)

  useEffect(() => {
    if (id) receiptApi.get(id).then(resp => setReceipt(resp.data))
  }, [id])

  if (!receipt) return <Card title="收款单详情">加载中...</Card>

  return (
    <Card title={`收款单详情 - ${receipt.receipt_number}`} extra={<Button onClick={() => navigate('/fin/receipts')}>返回</Button>}>
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="收款编号">{receipt.receipt_number}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{receipt.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="付款方">{receipt.payer}</Descriptions.Item>
        <Descriptions.Item label="金额">{formatMoney(receipt.amount, receipt.currency)}</Descriptions.Item>
        <Descriptions.Item label="币种">{receipt.currency}</Descriptions.Item>
        <Descriptions.Item label="到账日期">{receipt.received_at}</Descriptions.Item>
        <Descriptions.Item label="银行流水">{receipt.bank_ref_no || '-'}</Descriptions.Item>
        <Descriptions.Item label="核销时间">{receipt.written_off_at || '-'}</Descriptions.Item>
      </Descriptions>
      <Table
        columns={[
          { title: '关联单据', dataIndex: 'ref_doc', key: 'ref_doc' },
          { title: '核销金额', dataIndex: 'write_off_amount', key: 'write_off_amount', render: (v: string) => formatMoney(v, receipt.currency) },
          { title: '核销时间', dataIndex: 'write_off_at', key: 'write_off_at' },
        ]}
        dataSource={receipt.write_offs || []}
        rowKey="ref_doc"
        pagination={false}
      />
    </Card>
  )
}