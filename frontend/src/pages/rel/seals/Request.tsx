import { useState } from 'react'
import { Card, Form, Input, Button, message } from 'antd'
import { relApi } from '@/api/rel'
import { useNavigate } from 'react-router-dom'

export default function RelSealRequestPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (values: any) => {
    setLoading(true)
    try {
      const resp = await relApi.seal.request(values)
      message.success('封版请求已提交')
      navigate(`/rel/seals/${resp.data.release_id}`)
    } catch {
      message.error('封版请求失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="发起封版">
      <Form layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 600 }}>
        <Form.Item name="release_number" label="封版编号" rules={[{ required: true }]}>
          <Input placeholder="REL-2026-001" />
        </Form.Item>
        <Form.Item name="version" label="版本号" rules={[{ required: true }]}>
          <Input placeholder="1.0.0" />
        </Form.Item>
        <Form.Item name="git_tag" label="Git Tag" rules={[{ required: true }]}>
          <Input placeholder="v1.0.0" />
        </Form.Item>
        <Form.Item name="executed_by" label="执行人" rules={[{ required: true }]}>
          <Input placeholder="release-manager" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>提交封版请求</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}