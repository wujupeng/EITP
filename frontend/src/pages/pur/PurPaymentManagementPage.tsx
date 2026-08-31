import { useState, useEffect } from 'react'
import { Table, Button, message, Space, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { PaymentRequest } from '@/types/pur'

const STATUS_COLORS: Record<string, string> = {
  pending: 'default', executing: 'blue', completed: 'green', failed: 'red',
}

export default function PurPaymentManagementPage() {
  const [payments, setPayments] = useState<PaymentRequest[]>([])
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await purApi.payments.list()
      setPayments(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleConfirm = async (id: string) => {
    try {
      await purApi.payments.confirm(id, { paid: true })
      message.success('付款确认成功'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '付款编码', dataIndex: 'payment_code', key: 'payment_code' },
    { title: '结算单', dataIndex: 'settlement_id', key: 'settlement_id' },
    { title: '金额', dataIndex: 'amount', key: 'amount' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag> },
    { title: '操作', key: 'action',
      render: (_: unknown, r: PaymentRequest) => (
        <Space>
          {r.status === 'executing' && <Button size="small" type="primary" onClick={() => handleConfirm(r.payment_id)}>确认付款</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
      </Space>
      <Table columns={columns} dataSource={payments} rowKey="payment_id" loading={loading} pagination={{ pageSize: 20 }} />
    </div>
  )
}