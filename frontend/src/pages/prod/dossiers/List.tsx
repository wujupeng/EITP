import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Space } from 'antd'
import { prodApi } from '@/api/prod'
import { useNavigate } from 'react-router-dom'

export default function ProdDossierListPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const loadData = async () => {
    setLoading(true)
    try {
      const resp = await prodApi.dossier.list({ limit: 100 })
      setData(resp.data?.items || [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const columns = [
    { title: '证明书编号', dataIndex: 'dossier_number', key: 'dossier_number', render: (v: string, r: any) =>
      <a onClick={() => navigate(`/prod/dossiers/${r.dossier_id}`)}>{v}</a> },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const color = v === 'SIGNED' ? 'green' : v === 'INVALID' ? 'red' : 'blue'
      return <Tag color={color}>{v}</Tag>
    }},
    { title: '裁决', dataIndex: 'verdict', key: 'verdict', render: (v: string) => v ? <Tag color={v === 'READY' ? 'green' : 'red'}>{v}</Tag> : '-' },
    { title: '签发人', dataIndex: 'signer', key: 'signer' },
    { title: '签发时间', dataIndex: 'signed_at', key: 'signed_at' },
    { title: '有效期至', dataIndex: 'valid_until', key: 'valid_until' },
  ]

  return (
    <Card title="生产就绪证明书列表" extra={
      <Button type="primary" onClick={() => navigate('/prod/dossiers/assemble')}>汇编新证明书</Button>
    }>
      <Table columns={columns} dataSource={data} rowKey="dossier_id" loading={loading} />
    </Card>
  )
}