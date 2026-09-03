import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Table, Button, Form, Input, Select, message, Modal } from 'antd'
import { reconciliationApi } from '@/api/fin/reconciliation'
import { useParams, useNavigate } from 'react-router-dom'
import { formatMoney } from '@/utils/finMoney'

export default function ReconciliationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [recon, setRecon] = useState<any>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [currentDiff, setCurrentDiff] = useState<any>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    if (id) reconciliationApi.get(id).then(resp => setRecon(resp.data))
  }, [id])

  const handleDifference = async () => {
    try {
      const values = await form.validateFields()
      await reconciliationApi.handleDifference(currentDiff.diff_id, values)
      message.success('差异处理成功')
      setModalOpen(false)
      const resp = await reconciliationApi.get(id!)
      setRecon(resp.data)
    } catch {
      message.error('差异处理失败')
    }
  }

  if (!recon) return <Card title="对账详情">加载中...</Card>

  const diffColumns = [
    { title: '项目', dataIndex: 'item', key: 'item' },
    { title: '本方金额', dataIndex: 'local_amount', key: 'local_amount', render: (v: string) => formatMoney(v, recon.currency) },
    { title: '对方金额', dataIndex: 'remote_amount', key: 'remote_amount', render: (v: string) => formatMoney(v, recon.currency) },
    { title: '差异', dataIndex: 'diff_amount', key: 'diff_amount', render: (v: string) => <Tag color="red">{formatMoney(v, recon.currency)}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'RESOLVED' ? 'green' : 'orange'}>{v}</Tag> },
    { title: '操作', key: 'action', render: (_: any, record: any) => (
      <Button type="link" onClick={() => { setCurrentDiff(record); setModalOpen(true) }}>处理差异</Button>
    )},
  ]

  return (
    <Card title={`对账详情 - ${recon.batch_number}`} extra={<Button onClick={() => navigate('/fin/reconciliations')}>返回</Button>}>
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="批次号">{recon.batch_number}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{recon.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="对账类型">{recon.recon_type}</Descriptions.Item>
        <Descriptions.Item label="匹配数">{recon.matched_count}</Descriptions.Item>
        <Descriptions.Item label="差异数">{recon.diff_count}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{recon.created_at}</Descriptions.Item>
      </Descriptions>
      <Table columns={diffColumns} dataSource={recon.differences || []} rowKey="diff_id" pagination={false} />
      <Modal title="处理差异" open={modalOpen} onOk={handleDifference} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="handle_type" label="处理方式" rules={[{ required: true }]}>
            <Select options={['ADJUST', 'WRITE_OFF', 'ESCALATE'].map(t => ({ label: t, value: t }))} />
          </Form.Item>
          <Form.Item name="remark" label="处理说明">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}