import { useState } from 'react'
import { Card, Button, Form, Input, InputNumber, Space, Tag, message, Steps, List, Progress } from 'antd'
import { wmsApi } from '@/api/wms'
import type { Location } from '@/types/wms'

export default function WmsPutawayPage() {
  const [putawayId, setPutawayId] = useState('')
  const [suggestions, setSuggestions] = useState<Location[]>([])
  const [form] = Form.useForm()
  const [executing, setExecuting] = useState(false)
  const [warehouseId, setWarehouseId] = useState('')

  const loadSuggestions = async (whId: string) => {
    if (!whId) return
    try {
      const data = await wmsApi.space.listLocations(whId)
      setSuggestions(data.filter((l) => l.status === 'active'))
    } catch {
      message.error('加载库位建议失败')
    }
  }

  const handleExecute = async () => {
    const values = await form.validateFields()
    setExecuting(true)
    try {
      await wmsApi.putaway.execute(putawayId, {
        target_location_id: values.target_location_id,
        putaway_quantity: values.putaway_quantity,
      })
      message.success('上架执行成功')
      form.resetFields()
    } catch {
      message.error('上架执行失败')
    } finally {
      setExecuting(false)
    }
  }

  return (
    <Card title="上架作业台">
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="输入上架任务 ID"
          enterButton="加载"
          style={{ width: 400 }}
          onSearch={(val) => setPutawayId(val.trim())}
        />
        {putawayId && <Tag color="blue">当前任务: {putawayId.substring(0, 8)}...</Tag>}
      </Space>

      {putawayId && (
        <>
          <Steps
            size="small"
            current={1}
            items={[{ title: '创建上架任务' }, { title: '上架执行' }, { title: '完成' }]}
            style={{ marginBottom: 16 }}
          />
          <Space style={{ marginBottom: 16 }}>
            <Input
              placeholder="输入仓库 ID 获取库位建议"
              style={{ width: 300 }}
              onPressEnter={(e) => { const val = (e.target as HTMLInputElement).value.trim(); setWarehouseId(val); loadSuggestions(val) }}
            />
            <Button onClick={() => loadSuggestions(warehouseId)}>刷新建议</Button>
          </Space>

          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <Form form={form} layout="vertical">
                <Form.Item name="target_location_id" label="目标库位 ID" rules={[{ required: true }]}>
                  <Input placeholder="上架目标库位" />
                </Form.Item>
                <Form.Item name="putaway_quantity" label="上架数量" rules={[{ required: true }]}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
                <Button type="primary" onClick={handleExecute} loading={executing}>执行上架</Button>
              </Form>
            </div>
            <div style={{ flex: 1 }}>
              <Card title="库位建议" size="small">
                <List
                  size="small"
                  dataSource={suggestions.slice(0, 10)}
                  renderItem={(loc) => (
                    <List.Item
                      actions={[
                        <Button size="small" type="link" onClick={() => form.setFieldsValue({ target_location_id: loc.location_id })}>选择</Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={loc.location_code}
                        description={
                          <Space size="small">
                            <Tag>{loc.location_type}</Tag>
                            {loc.capacity_max_qty && (
                              <Progress
                                percent={0}
                                size="small"
                                format={() => `容量 ${loc.capacity_max_qty}`}
                                style={{ width: 120 }}
                              />
                            )}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                  locale={{ emptyText: '请输入仓库 ID 加载建议' }}
                />
              </Card>
            </div>
          </div>
        </>
      )}
    </Card>
  )
}
