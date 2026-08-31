import { useState } from 'react'
import { Card, Button, Form, Input, Space, Tag, message, Steps } from 'antd'
import { wmsApi } from '@/api/wms'

type ShippingPhase = 'pending' | 'logistics_recorded' | 'confirmed'

export default function WmsShippingPage() {
  const [shippingId, setShippingId] = useState('')
  const [phase, setPhase] = useState<ShippingPhase>('pending')
  const [form] = Form.useForm()
  const [executing, setExecuting] = useState(false)

  const handleRecordLogistics = async () => {
    const values = await form.validateFields()
    setExecuting(true)
    try {
      await wmsApi.shipping.execute(shippingId, {
        logistics_no: values.logistics_no,
        logistics_company: values.logistics_company,
      })
      message.success('物流信息录入成功')
      setPhase('logistics_recorded')
      form.resetFields()
    } catch {
      message.error('物流信息录入失败')
    } finally {
      setExecuting(false)
    }
  }

  const handleConfirm = async () => {
    setExecuting(true)
    try {
      await wmsApi.shipping.confirm(shippingId)
      message.success('发货确认成功')
      setPhase('confirmed')
    } catch {
      message.error('发货确认失败')
    } finally {
      setExecuting(false)
    }
  }

  const stepIndex = { pending: 0, logistics_recorded: 1, confirmed: 2 }[phase]

  return (
    <Card title="发货作业台">
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="输入发货单 ID"
          enterButton="加载"
          style={{ width: 400 }}
          onSearch={(val) => { setShippingId(val.trim()); setPhase('pending') }}
        />
        {shippingId && <Tag color="blue">当前发货单: {shippingId.substring(0, 8)}...</Tag>}
      </Space>

      {shippingId && (
        <>
          <Steps
            current={stepIndex}
            items={[{ title: '待发货' }, { title: '物流已录入' }, { title: '已确认发货' }]}
            style={{ marginBottom: 24 }}
          />

          {phase === 'pending' && (
            <Card title="录入物流信息" size="small">
              <Form form={form} layout="vertical" style={{ maxWidth: 400 }}>
                <Form.Item name="logistics_no" label="物流单号" rules={[{ required: true, message: '请输入物流单号' }]}>
                  <Input placeholder="如 SF1234567890" />
                </Form.Item>
                <Form.Item name="logistics_company" label="物流公司" rules={[{ required: true, message: '请输入物流公司' }]}>
                  <Input placeholder="如 顺丰速运" />
                </Form.Item>
                <Button type="primary" onClick={handleRecordLogistics} loading={executing}>录入物流</Button>
              </Form>
            </Card>
          )}

          {phase === 'logistics_recorded' && (
            <Button type="primary" onClick={handleConfirm} loading={executing}>确认发货</Button>
          )}

          {phase === 'confirmed' && <Tag color="green">发货已完成</Tag>}
        </>
      )}
    </Card>
  )
}
