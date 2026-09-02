import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Modal, Form, Input, Select } from 'antd'
import { pltApi } from '@/api/platform'

export default function CICDPipelinePage() {
  const [pipelines, setPipelines] = useState<any[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => { pltApi.cicd.pipelines().then(resp => setPipelines(resp.data.items || [])) }, [])

  return (
    <Card title="CI/CD 流水线" extra={<Button type="primary" onClick={() => setModalOpen(true)}>部署</Button>}>
      <Table dataSource={pipelines} rowKey="pipeline_id" columns={[
        { title: '流水线', dataIndex: 'name' },
        { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'SUCCESS' ? 'green' : v === 'FAILED' ? 'red' : 'blue'}>{v}</Tag> },
        { title: '操作', render: (_, r: any) => <Button size="small" onClick={() => pltApi.cicd.rollback(r.pipeline_id)}>回滚</Button> },
      ]} />
      <Modal title="部署" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => { form.validateFields().then(v => { pltApi.cicd.deploy(v); setModalOpen(false) }) }}>
        <Form form={form} layout="vertical">
          <Form.Item name="target" label="目标" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="version" label="版本" rules={[{ required: true }]}><Input /></Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}