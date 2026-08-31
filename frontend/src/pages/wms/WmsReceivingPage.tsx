import { useState } from 'react'
import { Card, Table, Button, Drawer, Form, Input, InputNumber, Space, Tag, message, Steps } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { wmsApi } from '@/api/wms'
import { generateIdempotencyKey } from '@/store/wms'

interface ReceivingLine {
  key: string
  line_id: string
  sku_id: string
  expected_quantity: number
  received_quantity: number
  status: string
}

export default function WmsReceivingPage() {
  const [receivingId, setReceivingId] = useState('')
  const [lines, setLines] = useState<ReceivingLine[]>([])
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [currentLine, setCurrentLine] = useState<ReceivingLine | null>(null)
  const [form] = Form.useForm()
  const [executing, setExecuting] = useState(false)

  const handleExecute = async () => {
    if (!currentLine) return
    const values = await form.validateFields()
    setExecuting(true)
    try {
      const idempotencyKey = generateIdempotencyKey()
      await wmsApi.receiving.execute(receivingId, {
        line_id: currentLine.line_id,
        received_quantity: values.received_quantity,
        location_id: values.location_id,
        lot_number: values.lot_number,
        batch_number: values.batch_number,
        serial_numbers: values.serial_numbers ? values.serial_numbers.split(',').map((s: string) => s.trim()).filter(Boolean) : [],
        idempotency_key: idempotencyKey,
      })
      message.success('收货执行成功')
      setDrawerOpen(false)
      form.resetFields()
      setLines((prev) => prev.map((l) => l.line_id === currentLine.line_id ? { ...l, received_quantity: l.received_quantity + values.received_quantity, status: 'partial' } : l))
    } catch {
      message.error('收货执行失败')
    } finally {
      setExecuting(false)
    }
  }

  const columns = [
    { title: '行项目 ID', dataIndex: 'line_id', key: 'line_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: 'SKU', dataIndex: 'sku_id', key: 'sku_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '预期数量', dataIndex: 'expected_quantity', key: 'expected_quantity' },
    { title: '已收数量', dataIndex: 'received_quantity', key: 'received_quantity', render: (v: number) => <Tag color={v > 0 ? 'green' : 'default'}>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{v}</Tag> },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: ReceivingLine) => (
        <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => { setCurrentLine(record); form.resetFields(); setDrawerOpen(true) }}>
          收货
        </Button>
      ),
    },
  ]

  return (
    <Card title="收货作业台">
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="输入收货单 ID"
          enterButton="加载"
          style={{ width: 400 }}
          onSearch={(val) => {
            setReceivingId(val.trim())
            setLines([])
          }}
        />
        {receivingId && <Tag color="blue">当前收货单: {receivingId.substring(0, 8)}...</Tag>}
      </Space>

      {receivingId && (
        <>
          <Steps
            size="small"
            current={1}
            items={[{ title: '创建收货单' }, { title: '收货执行' }, { title: '完成' }]}
            style={{ marginBottom: 16 }}
          />
          <Table columns={columns} dataSource={lines} rowKey="line_id" pagination={{ pageSize: 20 }} locale={{ emptyText: '请通过后端 API 创建收货单后加载行项目' }} />
        </>
      )}

      <Drawer
        title="收货执行"
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={480}
        footer={
          <Space style={{ float: 'right' }}>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleExecute} loading={executing}>确认收货</Button>
          </Space>
        }
      >
        {currentLine && (
          <Form form={form} layout="vertical">
            <Form.Item label="行项目"><Input value={currentLine.line_id} disabled /></Form.Item>
            <Form.Item label="SKU"><Input value={currentLine.sku_id} disabled /></Form.Item>
            <Form.Item label="预期数量"><InputNumber value={currentLine.expected_quantity} disabled style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="received_quantity" label="实收数量" rules={[{ required: true, message: '请输入收货数量' }]}>
              <InputNumber min={0} style={{ width: '100%' }} placeholder="输入实际收货数量" />
            </Form.Item>
            <Form.Item name="location_id" label="目标库位 ID" rules={[{ required: true, message: '请输入库位 ID' }]}>
              <Input placeholder="入库库位 ID" />
            </Form.Item>
            <Form.Item name="batch_number" label="批次号"><Input placeholder="可选" /></Form.Item>
            <Form.Item name="lot_number" label="LOT 号"><Input placeholder="可选" /></Form.Item>
            <Form.Item name="serial_numbers" label="序列号（逗号分隔）"><Input placeholder="SN001,SN002,..." /></Form.Item>
          </Form>
        )}
      </Drawer>
    </Card>
  )
}
