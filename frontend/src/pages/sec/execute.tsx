import { useState, useEffect } from 'react'
import { Card, Button, Select, Progress, Table, Tag, Space, message } from 'antd'
import { secApi } from '@/api/sec'
import { useSecStore } from '@/store/sec'

export default function SecExecutePage() {
  const [scope, setScope] = useState('full')
  const [loading, setLoading] = useState(false)
  const { batchId, batchProgress, setBatchId, setBatchProgress } = useSecStore()

  const handleExecute = async () => {
    setLoading(true)
    try {
      const resp = await secApi.executeCertification({ scope })
      setBatchId(resp.data.batch_id)
      message.success('认证已启动')
    } catch {
      message.error('启动失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!batchId) return
    const timer = setInterval(async () => {
      try {
        const resp = await secApi.getBatchProgress(batchId)
        setBatchProgress(resp.data)
        if (resp.data.status === 'completed' || resp.data.status === 'failed') {
          clearInterval(timer)
        }
      } catch { /* ignore */ }
    }, 3000)
    return () => clearInterval(timer)
  }, [batchId])

  const passRate = batchProgress ? (batchProgress.passed / batchProgress.total_items) * 100 : 0

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Card title="执行多租户隔离认证">
        <Space>
          <Select value={scope} onChange={setScope} style={{ width: 200 }} options={[
            { value: 'full', label: '全量认证' },
            { value: 'layers', label: '15层攻击矩阵' },
            { value: 'modules', label: '7模块全矩阵' },
            { value: 'redis', label: 'Redis Key隔离' },
            { value: 'visibility', label: '平台管理员可见性' },
            { value: 'join', label: 'JOIN泄露测试' },
            { value: 'e2e', label: '14步E2E攻击链' },
          ]} />
          <Button type="primary" loading={loading} onClick={handleExecute}>启动认证</Button>
        </Space>
      </Card>
      {batchProgress && (
        <Card title="执行进度">
          <Progress percent={passRate} status={batchProgress.status === 'completed' ? 'success' : 'active'} />
          <Space style={{ marginTop: 16 }}>
            <Tag>总计: {batchProgress.total_items}</Tag>
            <Tag color="green">通过: {batchProgress.passed}</Tag>
            <Tag color="red">失败: {batchProgress.failed}</Tag>
            <Tag color="orange">无法执行: {batchProgress.unexecutable}</Tag>
          </Space>
        </Card>
      )}
    </Space>
  )
}