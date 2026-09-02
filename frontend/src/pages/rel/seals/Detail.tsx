import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Steps, Button } from 'antd'
import { relApi } from '@/api/rel'
import { useParams, useNavigate } from 'react-router-dom'

const STATUS_STEPS = [
  'REQUESTED', 'GATE_RUNNING', 'SNAPSHOT_COLLECTING',
  'REPORT_ASSEMBLING', 'PENDING_CO_SIGN', 'SEALED',
]

export default function RelSealDetailPage() {
  const { releaseId } = useParams<{ releaseId: string }>()
  const navigate = useNavigate()
  const [seal, setSeal] = useState<any>(null)

  useEffect(() => {
    if (releaseId) relApi.seal.get(releaseId).then(resp => setSeal(resp.data))
  }, [releaseId])

  if (!seal) return <Card title="封版详情">加载中...</Card>

  const currentStep = STATUS_STEPS.indexOf(seal.seal_status)

  return (
    <Card title={`封版详情 - ${seal.release_number}`}>
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="封版编号">{seal.release_number}</Descriptions.Item>
        <Descriptions.Item label="版本">{seal.version}</Descriptions.Item>
        <Descriptions.Item label="Git Tag">{seal.git_tag}</Descriptions.Item>
        <Descriptions.Item label="Git Commit SHA">{seal.git_commit_sha || '-'}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{seal.seal_status}</Tag></Descriptions.Item>
        <Descriptions.Item label="裁决">{seal.verdict ? <Tag color={seal.verdict === 'FINAL_PASS' ? 'green' : 'red'}>{seal.verdict}</Tag> : '-'}</Descriptions.Item>
        <Descriptions.Item label="发布经理签发">{seal.signed_by_releaser || '-'}</Descriptions.Item>
        <Descriptions.Item label="安全负责人签发">{seal.signed_by_security || '-'}</Descriptions.Item>
        <Descriptions.Item label="核心冻结基线哈希">{seal.core_freeze_baseline_hash || '-'}</Descriptions.Item>
        <Descriptions.Item label="证据哈希">{seal.evidence_hash || '-'}</Descriptions.Item>
      </Descriptions>
      <Steps current={currentStep} items={STATUS_STEPS.map(s => ({ title: s }))} style={{ marginBottom: 16 }} />
      {seal.seal_status === 'PENDING_CO_SIGN' && (
        <Button type="primary" onClick={() => navigate(`/rel/seals/${releaseId}/co-sign`)}>联合签发</Button>
      )}
    </Card>
  )
}