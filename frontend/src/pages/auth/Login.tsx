import { useState } from 'react'
import { Card, Form, Input, Button, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { client } from '@/api/client'
import { useAuthStore } from '@/store/auth'

const { Title } = Typography

export default function Login() {
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const handleLogin = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      const response = await client.post('/auth/login', {
        tenant_id: values.tenant_id,
        username: values.username,
        password: values.password,
      })
      setAuth(response.data)
      message.success('登录成功')
      navigate('/')
    } catch {
      message.error('登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 32 }}>EITP 登录</Title>
        <Form form={form} layout="vertical" onFinish={handleLogin}>
          <Form.Item name="tenant_id" label="租户 ID" rules={[{ required: true }]}>
            <Input placeholder="请输入租户 ID" />
          </Form.Item>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}