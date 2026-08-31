import { useState } from 'react'
import { Form, Input, InputNumber, Select, Button, Card, message, Descriptions, Tag } from 'antd'
import { inventoryApi, type InventoryTransactionResult } from '@/api/inventory'

const TRANSACTION_TYPES = [
  { value: 'purchase_receipt', label: '采购入库' },
  { value: 'sales_issue', label: '销售出库' },
  { value: 'transfer_out', label: '调拨出库' },
  { value: 'transfer_in', label: '调拨入库' },
  { value: 'adjustment_in', label: '调整入库' },
  { value: 'adjustment_out', label: '调整出库' },
  { value: 'return_in', label: '退货入库' },
  { value: 'return_out', label: '退货出库' },
  { value: 'inspect_pass', label: '质检通过' },
  { value: 'inspect_fail', label: '质检不通过' },
  { value: 'block', label: '冻结' },
  { value: 'unblock', label: '解冻' },
]

function generateIdempotencyKey(): string {
  return 'idem-' + Date.now() + '-' + Math.random().toString(36).substring(2, 10)
}

export default function InventoryTransaction() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<InventoryTransactionResult | null>(null)

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setLoading(true)
    setResult(null)
    try {
      const res = await inventoryApi.executeTransaction({
        ...values,
        idempotency_key: values.idempotency_key || generateIdempotencyKey(),
      })
      setResult(res)
      message.success('库存事务执行成功')
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Card title="执行库存事务" style={{ maxWidth: 600 }}>
        <Form form={form} layout="vertical">
          <Form.Item name="sku_id" label="SKU ID" rules={[{ required: true }]}>
            <Input placeholder="SKU UUID" />
          </Form.Item>
          <Form.Item name="warehouse_id" label="仓库 ID" rules={[{ required: true }]}>
            <Input placeholder="仓库 UUID" />
          </Form.Item>
          <Form.Item name="transaction_type" label="事务类型" rules={[{ required: true }]}>
            <Select options={TRANSACTION_TYPES} placeholder="选择事务类型" />
          </Form.Item>
          <Form.Item name="quantity" label="数量" rules={[{ required: true, type: 'number', min: 0.01 }]}>
            <InputNumber min={0.01} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="unit_cost" label="单位成本">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="idempotency_key" label="幂等键（留空自动生成）">
            <Input placeholder="自动生成" />
          </Form.Item>
          <Form.Item name="reason" label="原因">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Button type="primary" loading={loading} onClick={handleSubmit}>
            执行事务
          </Button>
        </Form>
      </Card>
      {result && (
        <Card title="执行结果" style={{ maxWidth: 600, marginTop: 16 }}>
          <Descriptions column={1}>
            <Descriptions.Item label="事务 ID">{result.id}</Descriptions.Item>
            <Descriptions.Item label="类型">{result.transaction_type}</Descriptions.Item>
            <Descriptions.Item label="数量">{result.quantity}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={result.status === 'completed' ? 'green' : 'orange'}>{result.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="账本 ID">{result.result_ledger_id || '-'}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  )
}
