import { useState, useEffect } from 'react'
import { Table, Button, Modal, Form, Input, InputNumber, message, Space, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { purApi } from '@/api/pur'
import type { SupplierEvaluation } from '@/types/pur'

const GRADE_COLORS: Record<string, string> = {
  excellent: 'green', qualified: 'blue', unqualified: 'red',
}

export default function PurSupplierEvaluationPage() {
  const [evaluations, setEvaluations] = useState<SupplierEvaluation[]>([])
  const [loading, setLoading] = useState(false)
  const [supplierId, setSupplierId] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const loadData = async () => {
    if (!supplierId) return
    setLoading(true)
    try {
      const data = await purApi.suppliers.listEvaluations(supplierId)
      setEvaluations(data)
    } catch { /* handled by interceptor */ } finally { setLoading(false) }
  }

  useEffect(() => { if (supplierId) loadData() }, [supplierId])

  const handleCreate = async () => {
    const values = await form.validateFields()
    try {
      await purApi.suppliers.addEvaluation(supplierId, values)
      message.success('评估创建成功')
      setModalOpen(false); form.resetFields(); loadData()
    } catch { /* handled by interceptor */ }
  }

  const columns = [
    { title: '评估周期', dataIndex: 'evaluation_period', key: 'evaluation_period' },
    { title: '准时交货率', dataIndex: 'on_time_delivery_rate', key: 'on_time_delivery_rate',
      render: (v: number) => `${(v * 100).toFixed(1)}%` },
    { title: '质量合格率', dataIndex: 'quality_pass_rate', key: 'quality_pass_rate',
      render: (v: number) => `${(v * 100).toFixed(1)}%` },
    { title: '综合评分', dataIndex: 'overall_score', key: 'overall_score' },
    { title: '等级', dataIndex: 'grade', key: 'grade',
      render: (g: string) => <Tag color={GRADE_COLORS[g] || 'default'}>{g}</Tag> },
  ]

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input placeholder="输入供应商ID" value={supplierId} onChange={e => setSupplierId(e.target.value)} style={{ width: 300 }} />
        <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
        <Button type="primary" disabled={!supplierId} onClick={() => setModalOpen(true)}>新建评估</Button>
      </Space>
      <Table columns={columns} dataSource={evaluations} rowKey="evaluation_id" loading={loading} pagination={{ pageSize: 20 }} />
      <Modal title="新建供应商评估" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="evaluation_period" label="评估周期" rules={[{ required: true }]}><Input placeholder="如 2024-Q1" /></Form.Item>
          <Form.Item name="on_time_delivery_rate" label="准时交货率(0-1)" rules={[{ required: true }]}><InputNumber min={0} max={1} step={0.01} /></Form.Item>
          <Form.Item name="quality_pass_rate" label="质量合格率(0-1)" rules={[{ required: true }]}><InputNumber min={0} max={1} step={0.01} /></Form.Item>
          <Form.Item name="response_speed_score" label="响应速度评分(0-100)"><InputNumber min={0} max={100} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}