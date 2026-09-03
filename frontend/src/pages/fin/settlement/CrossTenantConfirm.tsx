import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Button, message, Alert } from 'antd'
import { settlementApi } from '@/api/fin/settlement'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function SettlementCrossTenantConfirmPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [settlement, setSettlement] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (id) settlementApi.get(id).then(resp => setSettlement(resp.data))
  }, [id])

  const handleConfirm = async () => {
    setLoading(true)
    try {
      await settlementApi.crossTenantConfirm(id!)
      message.success('跨租户结算确认成功')
      navigate(`/fin/settlements/${id}`)
    } catch {
      message.error('跨租户结算确认失败')
    } finally {
      setLoading(false)
    }
  }

  if (!settlement) return <Card title="跨租户结算确认">加载中...</Card>

  return (
    <Card title="跨租户结算确认">
      <Alert message="跨租户结算需要双方租户确认，请仔细核对结算信息" type="warning" showIcon style={{ marginBottom: 16 }} />
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="结算编号">{settlement.settlement_number}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="orange">{settlement.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="源租户">{settlement.source_tenant || '-'}</Descriptions.Item>
        <Descriptions.Item label="目标租户">{settlement.target_tenant || '-'}</Descriptions.Item>
        <Descriptions.Item label="交易方">{settlement.counterparty}</Descriptions.Item>
        <Descriptions.Item label="金额">{formatMoney(settlement.amount, settlement.currency)}</Descriptions.Item>
      </Descriptions>
      <Button type="primary" loading={loading} onClick={handleConfirm}>确认跨租户结算</Button>
    </Card>
  )
}