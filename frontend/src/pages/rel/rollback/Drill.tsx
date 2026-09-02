import { useState } from 'react'
import { Card, Form, Input, Button, message, Alert } from 'antd'
import { relApi } from '@/api/rel'
import { useParams, useNavigate } from 'react-router-dom'

export default function RelRollbackDrillPage() {
  const { releaseId } = useParams<{ releaseId: string }>()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (_values: any) => {
    setLoading(true)
    try {
      await relApi.rollback.drill(releaseId!, { drill_result: { executed: true } })
      message.success('回滚演练完成')
      navigate(`/rel/rollback/${releaseId}`)
    } catch {
      message.error('回滚演练失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="回滚演练">
      <Alert message="回滚演练将在隔离环境执行，验证迁移互逆性与配置回滚方案" type="info" showIcon style={{ marginBottom: 16 }} />
      <Form layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 600 }}>
        <Form.Item name="environment" label="演练环境" rules={[{ required: true }]}>
          <Input placeholder="staging" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>执行演练</Button>
        </Form.Item>
      </Form>
    </Card>
  )
}