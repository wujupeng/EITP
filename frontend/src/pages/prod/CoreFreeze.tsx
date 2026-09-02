import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, message, Descriptions } from 'antd'
import { prodApi } from '@/api/prod'

export default function ProdCoreFreezePage() {
  const [fingerprints, setFingerprints] = useState<any[]>([])
  const [verifyResult, setVerifyResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    prodApi.coreFreeze.fingerprints().then(resp => {
      setFingerprints(resp.data?.fingerprints || [])
    })
  }, [])

  const onVerify = async () => {
    setLoading(true)
    try {
      const resp = await prodApi.coreFreeze.verify()
      setVerifyResult(resp.data)
      if (resp.data.all_ok) {
        message.success('Core Freeze 校验通过')
      } else {
        message.warning(`检测到 ${resp.data.violation_count} 个违规`)
      }
    } catch {
      message.error('校验失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    { title: '里程碑', dataIndex: 'milestone', key: 'milestone' },
    { title: '资产类型', dataIndex: 'asset_type', key: 'asset_type' },
    { title: '资产路径', dataIndex: 'asset_path', key: 'asset_path' },
    { title: 'SHA-256', dataIndex: 'sha256', key: 'sha256', render: (v: string) => v?.slice(0, 16) + '...' },
  ]

  return (
    <Card title="Core Freeze 监控" extra={
      <Button type="primary" loading={loading} onClick={onVerify}>触发校验</Button>
    }>
      {verifyResult && (
        <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
          <Descriptions.Item label="校验结果">
            <Tag color={verifyResult.all_ok ? 'green' : 'red'}>{verifyResult.all_ok ? '通过' : '违规'}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="违规数">{verifyResult.violation_count}</Descriptions.Item>
        </Descriptions>
      )}
      <Table columns={columns} dataSource={fingerprints} rowKey={(r: any) => `${r.milestone}_${r.asset_type}`} />
    </Card>
  )
}