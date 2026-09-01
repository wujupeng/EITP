import { useState, useEffect } from 'react'
import { Card, Descriptions, Button, Tag, Space, message, Modal, Input } from 'antd'
import { secApi } from '@/api/sec'

export default function SecCertificatePage() {
  const [cert, setCert] = useState<any>(null)
  const [revokeModalOpen, setRevokeModalOpen] = useState(false)
  const [revokeReason, setRevokeReason] = useState('')

  const loadCert = () => secApi.getCurrentCertificate().then(resp => setCert(resp.data))

  useEffect(() => { loadCert() }, [])

  const handleIssue = async () => {
    try {
      await secApi.issueCertificate({ batch_id: '', issuer: 'admin', signer: 'security' })
      message.success('证书已颁发')
      loadCert()
    } catch { message.error('颁发失败') }
  }

  const handleRevoke = async () => {
    if (!cert?.certificate_id) return
    try {
      await secApi.revokeCertificate(cert.certificate_id, revokeReason)
      message.success('证书已撤销')
      setRevokeModalOpen(false)
      loadCert()
    } catch { message.error('撤销失败') }
  }

  const handleVerify = async () => {
    if (!cert?.certificate_id) return
    try {
      const resp = await secApi.verifyCertificate(cert.certificate_id)
      message.success(`校验结果: ${resp.data.overall_valid ? '有效' : '无效'}`)
    } catch { message.error('校验失败') }
  }

  return (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Card title="当前证书" extra={<Button type="primary" onClick={handleIssue}>颁发证书</Button>}>
        {cert?.cert_number ? (
          <Descriptions items={[
            { key: 'num', label: '证书编号', children: cert.cert_number },
            { key: 'status', label: '状态', children: <Tag color={cert.status === 'active' ? 'green' : 'red'}>{cert.status}</Tag> },
            { key: 'issued', label: '颁发时间', children: cert.issued_at },
            { key: 'valid', label: '有效期至', children: cert.valid_until },
          ]} />
        ) : <p>暂无证书</p>}
      </Card>
      {cert?.cert_number && (
        <Card title="证书操作">
          <Space>
            <Button onClick={handleVerify}>校验签名</Button>
            <Button danger onClick={() => setRevokeModalOpen(true)}>撤销证书</Button>
          </Space>
        </Card>
      )}
      <Modal title="撤销证书" open={revokeModalOpen} onOk={handleRevoke} onCancel={() => setRevokeModalOpen(false)}>
        <Input.TextArea value={revokeReason} onChange={e => setRevokeReason(e.target.value)} placeholder="撤销原因" />
      </Modal>
    </Space>
  )
}