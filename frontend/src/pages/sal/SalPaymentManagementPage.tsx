import { useState, useEffect } from 'react'
import { Table, Button, message, Space, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { salApi } from '@/api/sal'
import type { PaymentReceipt } from '@/types/sal'

const STATUS_COLORS: Record<string, string> = {
  pending: 'default', executing: 'blue', completed: 'green', failed: 'red',
}

export default function SalPaymentManagementPage() {
  const [payments, setPayments] = useState<PaymentReceipt[]>([])
  const [loading, setLoading] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await salApi.payments.list()
      setPayments(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [])

  const handleConfirm = async (id: string) => {
    try {
      await salApi.payments.confirm(id, { paid: true, paid_at: new Date().toISOString() })
      message.success('收款确认成功（触发信用额度释放）'); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '收款编码', dataIndex: 'payment_code', key: 'payment_code' },
    { title: '结算单', dataIndex: 'settlement_id', key: 'settlement_id' },
    { title: '客户ID', dataIndex: 'customer_id', key: 'customer_id' },
    { title: '金额', dataIndex: 'amount', key: 'amount' },
    { title: '收款方式', dataIndex: 'payment_method', key: 'payment_method' },
    {
      title: '状态', dataIndex: 'status', key: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s] || 'default'}>{s}</Tag>,
    },
    {
      title: '操作', key: 'action',
      render: (_: unknown, r: PaymentReceipt) => (
        <Space>
          {r.status === 'executing' && (
            <Button size="small" type="primary" onClick={() => handleConfirm(r.payment_id)}>确认收款</Button>
          )}
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