import { useState, useEffect } from 'react'
import { Card, Descriptions, Tag, Collapse, Button, Space, message } from 'antd'
import { prodApi } from '@/api/prod'
import { useParams, useNavigate } from 'react-router-dom'

export default function ProdDossierDetailPage() {
  const { dossier_id } = useParams()
  const [data, setData] = useState<any>({})
  const navigate = useNavigate()

  useEffect(() => {
    if (dossier_id) {
      prodApi.dossier.get(dossier_id).then(resp => setData(resp.data))
    }
  }, [dossier_id])

  const onExport = async () => {
    if (!dossier_id) return
    try {
      const resp = await prodApi.dossier.export(dossier_id)
      window.open(resp.data.export_url, '_blank')
    } catch {
      message.error('导出失败')
    }
  }

  const nineQuestions = data.nine_questions_answers || {}
  const collapseItems = Object.entries(nineQuestions).map(([key, val]: [string, any]) => ({
    key,
    label: key,
    children: (
      <Descriptions bordered column={1} size="small">
        <Descriptions.Item label="结论"><Tag color={val.conclusion === '能' ? 'green' : 'red'}>{val.conclusion}</Tag></Descriptions.Item>
        <Descriptions.Item label="证据">{JSON.stringify(val.evidence)}</Descriptions.Item>
        <Descriptions.Item label="详情">{JSON.stringify(val.details)}</Descriptions.Item>
      </Descriptions>
    ),
  }))

  return (
    <Card title={`证明书详情: ${data.dossier_number || dossier_id}`} extra={
      <Space>
        {data.status === 'PENDING_SIGN' && <Button type="primary" onClick={() => navigate(`/prod/dossiers/${dossier_id}/sign`)}>签发</Button>}
        <Button onClick={onExport}>导出PDF</Button>
      </Space>
    }>
      <Descriptions bordered column={2}>
        <Descriptions.Item label="编号">{data.dossier_number}</Descriptions.Item>
        <Descriptions.Item label="版本">{data.version}</Descriptions.Item>
        <Descriptions.Item label="状态"><Tag color="blue">{data.status}</Tag></Descriptions.Item>
        <Descriptions.Item label="裁决">{data.verdict}</Descriptions.Item>
        <Descriptions.Item label="证据聚合哈希">{data.evidence_aggregate_hash}</Descriptions.Item>
        <Descriptions.Item label="验证项数">{data.verification_run_ids?.length || 0}</Descriptions.Item>
        <Descriptions.Item label="签发人">{data.signer}</Descriptions.Item>
        <Descriptions.Item label="签发时间">{data.signed_at}</Descriptions.Item>
        <Descriptions.Item label="有效期至">{data.valid_until}</Descriptions.Item>
      </Descriptions>
      <Card type="inner" title="9 个关键问题回答" style={{ marginTop: 16 }}>
        <Collapse items={collapseItems} />
      </Card>
    </Card>
  )
}