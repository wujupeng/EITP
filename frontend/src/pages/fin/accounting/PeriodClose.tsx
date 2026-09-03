import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Form, Input, Modal, message, Steps, Alert } from 'antd'
import { accountingApi } from '@/api/fin/accounting'

const CLOSE_STEPS = ['PRE_CHECK', 'ACCRUAL', 'SETTLEMENT', 'CARRY_FORWARD', 'CLOSED']

export default function PeriodClosePage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await accountingApi.glVouchers.list()
      setData(res.data?.items || [])
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleClose = async () => {
    try {
      const values = await form.validateFields()
      await accountingApi.periodClose(values)
      message.success('期末结账已启动')
      setModalOpen(false)
      form.resetFields()
      fetchData()
    } catch {
      message.error('期末结账失败')
    }
  }

  const columns = [
    { title: '账期', dataIndex: 'period', key: 'period' },
    { title: '状态', dataIndex: 'close_status', key: 'close_status', render: (v: string) => <Tag color={v === 'CLOSED' ? 'green' : 'orange'}>{v}</Tag> },
    { title: '当前步骤', dataIndex: 'current_step', key: 'current_step' },
    { title: '操作人', dataIndex: 'operator', key: 'operator' },
    { title: '开始时间', dataIndex: 'started_at', key: 'started_at' },
    { title: '完成时间', dataIndex: 'finished_at', key: 'finished_at' },
  ]

  return (
    <Card title="期末结账" extra={<Button type="primary" onClick={() => setModalOpen(true)}>发起结账</Button>}>
      <Alert message="期末结账将依次执行预检、计提、结转、过账，请确认所有凭证已录入" type="warning" showIcon style={{ marginBottom: 16 }} />
      <Steps current={0} items={CLOSE_STEPS.map(s => ({ title: s }))} style={{ marginBottom: 16 }} />
      <Table columns={columns} dataSource={data} rowKey="period" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="发起期末结账" open={modalOpen} onOk={handleClose} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="period" label="账期" rules={[{ required: true }]}>
            <Input placeholder="2026-09" />
          </Form.Item>
          <Form.Item name="operator" label="操作人" rules={[{ required: true }]}>
            <Input placeholder="操作人账号" />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}