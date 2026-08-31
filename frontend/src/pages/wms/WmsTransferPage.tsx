import { useState } from 'react'
import { Card, Button, Form, Input, InputNumber, Space, Tag, message, Steps, Modal } from 'antd'
import { wmsApi } from '@/api/wms'

type TransferPhase = 'draft' | 'submitted' | 'approved' | 'executed'

export default function WmsTransferPage() {
  const [transferId, setTransferId] = useState('')
  const [phase, setPhase] = useState<TransferPhase>('draft')

  const [approveForm] = Form.useForm()
  const [executeForm] = Form.useForm()
  const [approveOpen, setApproveOpen] = useState(false)
  const [executing, setExecuting] = useState(false)

  const handleSubmit = async () => {
    setExecuting(true)
    try {
      await wmsApi.transfer.submit(transferId)
      message.success('移库单已提交审批')
      setPhase('submitted')
    } catch {
      message.error('提交失败')
    } finally {
      setExecuting(false)
    }
  }

  const handleApprove = async () => {
    const values = await approveForm.validateFields()
    setExecuting(true)
    try {
      await wmsApi.transfer.approve(transferId, { opinion: values.opinion })
      message.success('审批通过')
      setPhase('approved')
      setApproveOpen(false)
      approveForm.resetFields()
    } catch {
      message.error('审批失败')
    } finally {
      setExecuting(false)
    }
  }

  const handleExecute = async () => {
    const values = await executeForm.validateFields()
    setExecuting(true)
    try {
      await wmsApi.transfer.execute(transferId, {
        line_id: values.line_id,
        transfer_quantity: values.transfer_quantity,
      })
      message.success('移库执行成功')
      setPhase('executed')
      executeForm.resetFields()
    } catch {
      message.error('移库执行失败')
    } finally {
      setExecuting(false)
    }
  }

  const stepIndex = { draft: 0, submitted: 1, approved: 2, executed: 3 }[phase]

  return (
    <Card title="移库作业台">
      <Space style={{ marginBottom: 16 }}>
        <Input.Search
          placeholder="输入移库单 ID"
          enterButton="加载"
          style={{ width: 400 }}
          onSearch={(val) => { setTransferId(val.trim()); setPhase('draft') }}
        />
        {transferId && <Tag color="blue">当前移库单: {transferId.substring(0, 8)}...</Tag>}
      </Space>

      {transferId && (
        <>
          <Steps
            current={stepIndex}
            items={[{ title: '草稿' }, { title: '已提交' }, { title: '已审批' }, { title: '已执行' }]}
            style={{ marginBottom: 24 }}
          />

          <Space direction="vertical" style={{ width: '100%' }}>
            {phase === 'draft' && (
              <Button type="primary" onClick={handleSubmit} loading={executing}>提交审批</Button>
            )}

            {phase === 'submitted' && (
              <Button type="primary" onClick={() => setApproveOpen(true)}>审批</Button>
            )}

            {phase === 'approved' && (
              <Card title="执行移库" size="small">
                <Form form={executeForm} layout="inline">
                  <Form.Item name="line_id" label="行项目 ID" rules={[{ required: true }]}>
                    <Input placeholder="移库行项目 ID" />
                  </Form.Item>
                  <Form.Item name="transfer_quantity" label="移库数量" rules={[{ required: true }]}>
                    <InputNumber min={0} />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" onClick={handleExecute} loading={executing}>执行移库</Button>
                  </Form.Item>
                </Form>
              </Card>
            )}

            {phase === 'executed' && <Tag color="green">移库已完成</Tag>}
          </Space>
        </>
      )}

      <Modal title="审批移库单" open={approveOpen} onOk={handleApprove} onCancel={() => setApproveOpen(false)} confirmLoading={executing}>
        <Form form={approveForm} layout="vertical">
          <Form.Item name="opinion" label="审批意见">
            <Input.TextArea placeholder="输入审批意见（可选）" rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
