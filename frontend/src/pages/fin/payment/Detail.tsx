import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Table, Button } from 'antd'
import { paymentApi } from '@/api/fin/payment'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function PaymentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [payment, setPayment] = useState<any>(null)

  useEffect(() => {
    if (id) paymentApi.get(id).then(resp => setPayment(resp.data))
  }, [id])

  if (!payment) return <Card title="付款单详情">加载中...</Card>

  return (
    <Card title={`付款单详情 - ${payment.payment_number}`} extra={<Button onClick={() => navigate('/fin/payments')}>返回</Button>}>
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="付款编号">{payment.payment_number}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{payment.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="收款方">{payment.payee}</Descriptions.Item>
        <Descriptions.Item label="收款账户">{payment.payee_account || '-'}</Descriptions.Item>
        <Descriptions.Item label="金额">{formatMoney(payment.amount, payment.currency)}</Descriptions.Item>
        <Descriptions.Item label="币种">{payment.currency}</Descriptions.Item>
        <Descriptions.Item label="付款用途">{payment.purpose || '-'}</Descriptions.Item>
        <Descriptions.Item label="申请日期">{payment.requested_at}</Descriptions.Item>
        <Descriptions.Item label="审批人">{payment.approver || '-'}</Descriptions.Item>
        <Descriptions.Item label="执行时间">{payment.executed_at || '-'}</Descriptions.Item>
      </Descriptions>
      <Table
        columns={[
          { title: '银行流水号', dataIndex: 'bank_ref_no', key: 'bank_ref_no' },
          { title: '回调时间', dataIndex: 'callback_at', key: 'callback_at' },
          { title: '结果', dataIndex: 'result', key: 'result', render: (v: string) => <Tag color={v === 'SUCCESS' ? 'green' : 'red'}>{v}</Tag> },
        ]}
        dataSource={payment.callbacks || []}
        rowKey="bank_ref_no"
        pagination={false}
      />
    </Card>
  )
}