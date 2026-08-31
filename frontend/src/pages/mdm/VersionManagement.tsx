import { useState } from 'react'
import { Card, Table, Button, Form, Input, Select, Space, Tag, message, Modal, InputNumber, Typography, Divider } from 'antd'
import { SearchOutlined, DiffOutlined } from '@ant-design/icons'
import { versionApi } from '@/api/mdm'
import type { MasterDataVersion, VersionCompareResult } from '@/api/mdm/types'

const { Text } = Typography

export default function VersionManagement() {
  const [versions, setVersions] = useState<MasterDataVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [compareModalOpen, setCompareModalOpen] = useState(false)
  const [compareResult, setCompareResult] = useState<VersionCompareResult | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)
  const [searchForm] = Form.useForm()
  const [compareForm] = Form.useForm()

  const handleSearch = async () => {
    const values = await searchForm.validateFields()
    setLoading(true)
    try {
      const list = await versionApi.listGroup(values.entity_type, values.entity_id)
      setVersions(list)
    } catch {
      message.error('查询版本历史失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCompare = async () => {
    const values = await compareForm.validateFields()
    setCompareLoading(true)
    try {
      const result = await versionApi.compare({
        entity_type: values.entity_type,
        entity_id: values.entity_id,
        version_a: values.version_a,
        version_b: values.version_b,
      })
      setCompareResult(result)
    } catch {
      message.error('版本对比失败')
    } finally {
      setCompareLoading(false)
    }
  }

  const columns = [
    { title: '版本号', dataIndex: 'version_number', key: 'version_number', render: (v: number) => <Tag color="blue">v{v}</Tag> },
    { title: '变更类型', dataIndex: 'change_type', key: 'change_type', render: (t: string) => <Tag>{t}</Tag> },
    { title: '操作人', dataIndex: 'operated_by', key: 'operated_by', render: (id: string) => id.substring(0, 8) + '...' },
    { title: '操作时间', dataIndex: 'operated_at', key: 'operated_at' },
    { title: '原因', dataIndex: 'reason', key: 'reason', render: (r: string | null) => r || '-' },
    {
      title: '快照',
      key: 'snapshot',
      render: (_: unknown, record: MasterDataVersion) => (
        <Space>
          <Text type="secondary">before: {record.snapshot_before ? '有' : '无'}</Text>
          <Text type="secondary">after: {record.snapshot_after ? '有' : '无'}</Text>
        </Space>
      ),
    },
  ]

  return (
    <Card>
      <Form form={searchForm} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="entity_type" label="实体类型" rules={[{ required: true }]}>
          <Select
            style={{ width: 150 }}
            options={[
              { label: '集团商品', value: 'group_product' },
              { label: '企业商品', value: 'enterprise_product' },
              { label: '规格模板', value: 'spec_template' },
              { label: '属性模板', value: 'attribute_template' },
            ]}
          />
        </Form.Item>
        <Form.Item name="entity_id" label="实体ID" rules={[{ required: true }]}>
          <Input placeholder="实体 UUID" style={{ width: 300 }} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>查询</Button>
            <Button icon={<DiffOutlined />} onClick={() => setCompareModalOpen(true)}>版本对比</Button>
          </Space>
        </Form.Item>
      </Form>

      <Table
        columns={columns}
        dataSource={versions}
        rowKey="version_id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />

      <Modal
        title="版本对比"
        open={compareModalOpen}
        onCancel={() => { setCompareModalOpen(false); setCompareResult(null) }}
        footer={null}
        width={800}
      >
        <Form form={compareForm} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="entity_type" label="实体类型" rules={[{ required: true }]}>
            <Select
              style={{ width: 150 }}
              options={[
                { label: '集团商品', value: 'group_product' },
                { label: '企业商品', value: 'enterprise_product' },
                { label: '规格模板', value: 'spec_template' },
                { label: '属性模板', value: 'attribute_template' },
              ]}
            />
          </Form.Item>
          <Form.Item name="entity_id" label="实体ID" rules={[{ required: true }]}>
            <Input placeholder="实体 UUID" style={{ width: 250 }} />
          </Form.Item>
          <Form.Item name="version_a" label="版本A" rules={[{ required: true }]}>
            <InputNumber min={1} placeholder="1" />
          </Form.Item>
          <Form.Item name="version_b" label="版本B" rules={[{ required: true }]}>
            <InputNumber min={1} placeholder="2" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" icon={<DiffOutlined />} loading={compareLoading} onClick={handleCompare}>对比</Button>
          </Form.Item>
        </Form>

        {compareResult && (
          <>
            <Divider>对比结果</Divider>
            <Table
              size="small"
              dataSource={Object.entries(compareResult).map(([field, diff]) => ({
                key: field,
                field,
                before: diff.before,
                after: diff.after,
              }))}
              columns={[
                { title: '字段', dataIndex: 'field', key: 'field' },
                {
                  title: '版本A',
                  dataIndex: 'before',
                  key: 'before',
                  render: (v: unknown) => <Text>{JSON.stringify(v)}</Text>,
                },
                {
                  title: '版本B',
                  dataIndex: 'after',
                  key: 'after',
                  render: (v: unknown) => <Text>{JSON.stringify(v)}</Text>,
                },
              ]}
              pagination={false}
            />
          </>
        )}
      </Modal>
    </Card>
  )
}
