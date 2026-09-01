import { useState } from 'react'
import { Card, Button, Table, Tag, Steps, Space, message } from 'antd'
import { secApi } from '@/api/sec'

export default function SecAttackChainPage() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handleExecute = async () => {
    setLoading(true)
    try {
      const resp = await secApi.executeAttackChain()
      setResult(resp.data)
      message.success('攻击链执行完成')
    } catch { message.error('执行失败') }
    finally { setLoading(false) }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Card title="14 步攻击链 E2E 验证" extra={<Button type="primary" loading={loading} onClick={handleExecute}>执行攻击链</Button>}>
        {result && (
          <Steps direction="vertical" current={result.passed_steps + result.failed_steps} items={(result.results || []).map((r: any, i: number) => ({
            title: `步骤 ${i + 1}: ${r.description}`,
            status: r.is_blocked ? 'finish' : 'error',
            description: r.is_blocked ? '已拦截' : r.error || '未拦截',
          }))} />
        )}
      </Card>
    </Space>
  )
}