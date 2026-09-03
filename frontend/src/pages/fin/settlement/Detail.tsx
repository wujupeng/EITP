import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Table, Button } from 'antd'
import { settlementApi } from '@/api/fin/settlement'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function SettlementDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [settlement, setSettlement] = useState<any>(null)

  useEffect(() => {
    if (id) settlementApi.get(id).then(resp => setSettlement(resp.data))
  }, [id])

  if (!settlement) return <Card title="结算单详情">加载中...</Card>

  const detailColumns = [
    { title: '行号', dataIndex: 'line_no', key: 'line_no' },
    { title: '摘要', dataIndex: 'summary', key: 'summary' },
    { title: '金额', dataIndex: 'amount', key: 'amount', render: (v: string) => formatMoney(v, settlement.currency) },
    { title: '方向', dataIndex: 'direction', key: 'direction', render: (v: string) => <Tag color={v === 'DEBIT' ? 'green' : 'red'}>{v}</Tag> },
  ]

  return (
    <Card title={`结算单详情 - ${settlement.settlement_number}`} extra={<Button onClick={() => navigate('/fin/settlements')}>返回</Button>}>
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="结算编号">{settlement.settlement_number}</Descriptions.Item>
        <Descriptions.Item label="类型"><Tag color="blue">{settlement.settlement_type}</Tag></Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color={settlement.status === 'CONFIRMED' ? 'green' : 'orange'}>{settlement.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="交易方">{settlement.counterparty}</Descriptions.Item>
        <Descriptions.Item label="金额">{formatMoney(settlement.amount, settlement.currency)}</Descriptions.Item>
        <Descriptions.Item label="币种">{settlement.currency}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{settlement.created_at}</Descriptions.Item>
        <Descriptions.Item label="确认时间">{settlement.confirmed_at || '-'}</Descriptions.Item>
      </Descriptions>
      <Table columns={detailColumns} dataSource={settlement.details || []} rowKey="line_no" pagination={false} />
    </Card>
  )
}