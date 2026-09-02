import { useState } from 'react'
import { Card, Form, Input, Button, message, Alert } from 'antd'
import { prodApi } from '@/api/prod'
import { useParams, useNavigate } from 'react-router-dom'

export default function ProdDossierSignPage() {
  const { dossier_id } = useParams()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const onSign = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      await prodApi.dossier.sign(dossier_id!, {
        signer_id: values.signer_id,
        tenant_id: values.tenant_id,
      })
      message.success('证明书签发成功')
      navigate(`/prod/dossiers/${dossier_id}`)
    } catch {
      message.error('签发失败，请检查权限')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="证明书签发">
      <Alert
        message="安全负责人签发"
        description="仅安全负责人（SEC_OFF）角色可签发生产就绪证明书。签发后证明书状态变为 SIGNED，裁决为 FINAL PASS。"
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <Form form={form} layout="vertical">
        <Form.Item name="signer_id" label="签发人ID" rules={[{ required: true }]}>
          <Input placeholder="请输入安全负责人用户ID" />
        </Form.Item>
        <Form.Item name="tenant_id" label="租户ID" rules={[{ required: true }]}>
          <Input placeholder="请输入租户ID" />
        </Form.Item>
        <Button type="primary" loading={loading} onClick={onSign}>确认签发</Button>
      </Form>
    </Card>
  )
}