import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Button, Space, message } from 'antd'
import { prodApi } from '@/api/prod'
import { useParams } from 'react-router-dom'

export default function ProdVerificationDetailPage() {
  const { run_id } = useParams()
  const [data, setData] = useState<any>({})
  const [evidence, setEvidence] = useState<any[]>([])

  useEffect(() => {
    if (run_id) {
      prodApi.verification.get(run_id).then(resp => setData(resp.data))
      prodApi.evidence.list({ run_id }).then(resp => setEvidence(resp.data?.items || []))
    }
  }, [run_id])

  const onRetry = async () => {
    if (!run_id) return
    try {
      await prodApi.verification.retry(run_id)
      message.success('重执行已提交')
    } catch {
      message.error('重执行失败')
    }
  }

  return (
    <Card title={`验证详情: ${run_id}`} extra={
      <Button onClick={onRetry}>重执行</Button>
    }>
      <Descriptions bordered column={2}>
        <Descriptions.Item label="验证项">{data.verification_item}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{data.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="结论">{data.conclusion}</Descriptions.Item>
        <Descriptions.Item label="执行人">{data.executor}</Descriptions.Item>
        <Descriptions.Item label="环境">{data.environment}</Descriptions.Item>
        <Descriptions.Item label="Trace ID">{data.trace_id}</Descriptions.Item>
        <Descriptions.Item label="证据哈希">{data.evidence_hash}</Descriptions.Item>
        <Descriptions.Item label="失败明细">{JSON.stringify(data.failure_detail || {})}</Descriptions.Item>
      </Descriptions>
      <Card type="inner" title="证据三元组" style={{ marginTop: 16 }}>
        {evidence.map((ev: any) => (
          <Descriptions key={ev.evidence_id} bordered column={2} size="small" style={{ marginBottom: 8 }}>
            <Descriptions.Item label="类型">{ev.evidence_type}</Descriptions.Item>
            <Descriptions.Item label="哈希">{ev.content_hash}</Descriptions.Item>
            <Descriptions.Item label="大小">{ev.size_bytes} bytes</Descriptions.Item>
            <Descriptions.Item label="路径">{ev.storage_path}</Descriptions.Item>
          </Descriptions>
        ))}
      </Card>
    </Card>
  )
}