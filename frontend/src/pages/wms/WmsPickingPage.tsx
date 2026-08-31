import { useState } from 'react'
import { Card, Table, Button, Form, Input, InputNumber, Space, Tag, message, Steps } from 'antd'
import { wmsApi } from '@/api/wms'

interface PickingLine {
  key: string
  line_id: string
  sku_id: string
  location_id: string
  required_quantity: number
  picked_quantity: number
  status: string
}

export default function WmsPickingPage() {
  const [pickingId, setPickingId] = useState('')
  const [lines, setLines] = useState<PickingLine[]>([])
  const [form] = Form.useForm()
  const [currentLine, setCurrentLine] = useState<PickingLine | null>(null)
  const [executing, setExecuting] = useState(false)

  const handleExecute = async () => {
    if (!currentLine) return
    const values = await form.validateFields()
    setExecuting(true)
    try {
      await wmsApi.picking.execute(pickingId, {
        line_id: currentLine.line_id,
        picked_quantity: values.picked_quantity,
      })
      message.success('拣货执行成功')
      setLines((prev) => prev.map((l) => l.line_id === currentLine.line_id ? { ...l, picked_quantity: values.picked_quantity, status: 'picked' } : l))
      setCurrentLine(null)
      form.resetFields()
    } catch {
      message.error('拣货执行失败')
    } finally {
      setExecuting(false)
    }
  }

  const columns = [
    { title: '行项目', dataIndex: 'line_id', key: 'line_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: 'SKU', dataIndex: 'sku_id', key: 'sku_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '源库位', dataIndex: 'location_id', key: 'location_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '需求数量', dataIndex: 'required_quantity', key: 'required_quantity' },
    { title: '已拣数量', dataIndex: 'picked_quantity', key: 'picked_quantity', render: (v: number) => <Tag color={v > 0 ? 'green' : 'default'}>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{v}</Tag> },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: PickingLine) => (
        <Button type="primary" size="small" onClick={() => { setCurrentLine(record); form.setFieldsValue({ picked_quantity: record.required_quantity }) }}>
          拣货
        </Button>
      ),
    },
  ]

  return (
    <Card title="拣货作业台">
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="输入拣货任务 ID"
          enterButton="加载"
          style={{ width: 400 }}
          onSearch={(val) => { setPickingId(val.trim()); setLines([]) }}
        />
        {pickingId && <Tag color="blue">当前任务: {pickingId.substring(0, 8)}...</Tag>}
      </Space>

      {pickingId && (
        <>
          <Steps
            size="small"
            current={1}
            items={[{ title: '创建拣货任务' }, { title: '拣货执行' }, { title: '完成' }]}
            style={{ marginBottom: 16 }}
          />
          <Table columns={columns} dataSource={lines} rowKey="line_id" pagination={{ pageSize: 20 }} locale={{ emptyText: '请通过后端 API 创建拣货任务后加载行项目' }} />

          {currentLine && (
            <Card title="拣货确认" size="small" style={{ marginTop: 16 }}>
              <Form form={form} layout="inline">
                <Form.Item label="行项目"><Input value={currentLine.line_id} disabled /></Form.Item>
                <Form.Item label="源库位"><Input value={currentLine.location_id} disabled /></Form.Item>
                <Form.Item name="picked_quantity" label="拣货数量" rules={[{ required: true }]}>
                  <InputNumber min={0} />
                </Form.Item>
                <Form.Item>
                  <Space>
                    <Button type="primary" onClick={handleExecute} loading={executing}>确认拣货</Button>
                    <Button onClick={() => { setCurrentLine(null); form.resetFields() }}>取消</Button>
                  </Space>
                </Form.Item>
              </Form>
            </Card>
          )}
        </>
      )}
    </Card>
  )
}
