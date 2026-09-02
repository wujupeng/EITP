import { useState } from 'react'
import { Card, Form, Input, Button, message, Alert } from 'antd'
import { relApi } from '@/api/rel'
import { useParams, useNavigate } from 'react-router-dom'

export default function RelSealCoSignPage() {
  const { releaseId } = useParams<{ releaseId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      await relApi.seal.coSign(releaseId!, values)
      message.success('联合签发成功，封版已完成')
      navigate(`/rel/seals/${releaseId}`)
    } catch {
      message.error('联合签发失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="联合签发">
      <Alert message="联合签发需要发布经理和安全负责人双方凭证，禁止同一人代签" type="warning" showIcon style={{ marginBottom: 16 }} />
      <Form layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 600 }}>
        <Form.Item name="releaser" label="发布经理" rules={[{ required: true }]}>
          <Input placeholder="release-manager" />
        </Form.Item>
        <Form.Item name="security_officer" label="安全负责人" rules={[{ required: true }]}>
          <Input placeholder="security-officer" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>联合签发</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}