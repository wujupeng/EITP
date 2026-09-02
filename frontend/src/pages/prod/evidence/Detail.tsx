import { useState, useEffect } from 'react'
import { Card, Descriptions, Button, message, Tabs } from 'antd'
import { prodApi } from '@/api/prod'
import { useParams } from 'react-router-dom'

export default function ProdEvidenceDetailPage() {
  const { evidence_id } = useParams()
  const [data, setData] = useState<any>({})

  useEffect(() => {
    if (evidence_id) {
      prodApi.evidence.get(evidence_id).then(resp => setData(resp.data))
    }
  }, [evidence_id])

  const onVerifyHash = async () => {
    if (!evidence_id) return
    try {
      const resp = await prodApi.evidence.verifyHash({
        evidence_id,
        stored_hash: data.content_hash,
        content_ref: data.storage_path,
      })
      message.success(`哈希校验: ${resp.data.integrity_ok ? '通过' : '失败'}`)
    } catch {
      message.error('哈希校验失败')
    }
  }

  const onDownload = async () => {
    if (!evidence_id) return
    try {
      const resp = await prodApi.evidence.download(evidence_id)
      window.open(resp.data.download_url, '_blank')
    } catch {
      message.error('下载失败')
    }
  }

  return (
    <Card title={`证据详情: ${evidence_id}`} extra={
      <Tabs items={[
        { key: 'verify', label: '哈希校验', children: null },
      ]} />
    }>
      <Descriptions bordered column={2}>
        <Descriptions.Item label="类型">{data.evidence_type}</Descriptions.Item>
        <Descriptions.Item label="Run ID">{data.run_id}</Descriptions.Item>
        <Descriptions.Item label="存储路径">{data.storage_path}</Descriptions.Item>
        <Descriptions.Item label="内容哈希">{data.content_hash}</Descriptions.Item>
        <Descriptions.Item label="大小">{data.size_bytes} bytes</Descriptions.Item>
        <Descriptions.Item label="Trace ID">{data.trace_id}</Descriptions.Item>
      </Descriptions>
      <div style={{ marginTop: 16 }}>
        <Button type="primary" onClick={onVerifyHash} style={{ marginRight: 8 }}>校验哈希</Button>
        <Button onClick={onDownload}>下载制品</Button>
      </div>
    </Card>
  )
}