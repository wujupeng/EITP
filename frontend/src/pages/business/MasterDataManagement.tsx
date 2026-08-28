import { useState } from 'react'
import { Card, Typography, Form, Input, Button, Space, Tabs, Descriptions, message, Divider } from 'antd'
import { client } from '@/api/client'

const { Title, Paragraph } = Typography

interface MasterDataSku {
  id: string
  enterprise_id: string
  sku_code: string
  base_attrs: Record<string, unknown>
  version: number
}

interface EffectiveSku {
  master_data_id: string
  organization_id: string | null
  warehouse_id: string | null
  effective_attrs: Record<string, unknown>
  base_version: number
}

export default function MasterDataManagement() {
  const [baseForm] = Form.useForm()
  const [companyForm] = Form.useForm()
  const [warehouseForm] = Form.useForm()
  const [effectiveForm] = Form.useForm()
  const [createdSku, setCreatedSku] = useState<MasterDataSku | null>(null)
  const [effectiveResult, setEffectiveResult] = useState<EffectiveSku | null>(null)

  const handleCreateBase = async () => {
    const values = await baseForm.validateFields()
    try {
      const attrs = JSON.parse(values.base_attrs_json || '{}')
      const response = await client.post<MasterDataSku>('/master-data/sku', {
        enterprise_id: values.enterprise_id,
        sku_code: values.sku_code,
        base_attrs: attrs,
      })
      setCreatedSku(response.data)
      message.success('集团主数据基准创建成功')
    } catch {
      message.error('创建失败')
    }
  }

  const handleSetCompanyOverride = async () => {
    const values = await companyForm.validateFields()
    try {
      const attrs = JSON.parse(values.company_attrs_json || '{}')
      await client.put(`/master-data/sku/${values.sku_id}/company-override`, {
        organization_id: values.organization_id,
        company_attrs: attrs,
      })
      message.success('公司级属性覆盖设置成功')
    } catch {
      message.error('设置失败')
    }
  }

  const handleSetWarehouseOverride = async () => {
    const values = await warehouseForm.validateFields()
    try {
      const attrs = JSON.parse(values.warehouse_attrs_json || '{}')
      await client.put(`/master-data/sku/${values.sku_id}/warehouse-override`, {
        warehouse_id: values.warehouse_id,
        warehouse_attrs: attrs,
      })
      message.success('仓库级属性覆盖设置成功')
    } catch {
      message.error('设置失败')
    }
  }

  const handleGetEffective = async () => {
    const values = await effectiveForm.validateFields()
    try {
      const params: Record<string, string> = {}
      if (values.organization_id) params.organization_id = values.organization_id
      if (values.warehouse_id) params.warehouse_id = values.warehouse_id
      const response = await client.get<EffectiveSku>(
        `/master-data/sku/${values.sku_id}/effective`,
        { params },
      )
      setEffectiveResult(response.data)
    } catch {
      message.error('查询失败')
    }
  }

  return (
    <Card>
      <Title level={3}>主数据管理 - 三层继承</Title>
      <Paragraph>
        集团基准 → 公司级覆盖 → 仓库级覆盖。最终生效值 = base_attrs ∪ company_attrs ∪ warehouse_attrs（后者覆盖前者同名键）。
      </Paragraph>

      <Tabs
        items={[
          {
            key: 'base',
            label: '集团基准',
            children: (
              <Form form={baseForm} layout="vertical" style={{ maxWidth: 600 }}>
                <Form.Item name="enterprise_id" label="Enterprise ID" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Form.Item name="sku_code" label="SKU 编码" rules={[{ required: true }]}>
                  <Input placeholder="SKU-001" />
                </Form.Item>
                <Form.Item name="base_attrs_json" label="基准属性 (JSON)">
                  <Input.TextArea placeholder='{"name":"商品A","unit":"个"}' rows={4} />
                </Form.Item>
                <Button type="primary" onClick={handleCreateBase}>创建基准</Button>
                {createdSku && (
                  <>
                    <Divider />
                    <Descriptions title="已创建基准" column={1} bordered>
                      <Descriptions.Item label="ID">{createdSku.id}</Descriptions.Item>
                      <Descriptions.Item label="SKU 编码">{createdSku.sku_code}</Descriptions.Item>
                      <Descriptions.Item label="版本">{createdSku.version}</Descriptions.Item>
                      <Descriptions.Item label="基准属性">
                        {JSON.stringify(createdSku.base_attrs)}
                      </Descriptions.Item>
                    </Descriptions>
                  </>
                )}
              </Form>
            ),
          },
          {
            key: 'company',
            label: '公司级覆盖',
            children: (
              <Form form={companyForm} layout="vertical" style={{ maxWidth: 600 }}>
                <Form.Item name="sku_id" label="SKU ID" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Form.Item name="organization_id" label="Organization ID" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Form.Item name="company_attrs_json" label="公司级属性 (JSON)">
                  <Input.TextArea placeholder='{"price":100}' rows={4} />
                </Form.Item>
                <Button type="primary" onClick={handleSetCompanyOverride}>设置覆盖</Button>
              </Form>
            ),
          },
          {
            key: 'warehouse',
            label: '仓库级覆盖',
            children: (
              <Form form={warehouseForm} layout="vertical" style={{ maxWidth: 600 }}>
                <Form.Item name="sku_id" label="SKU ID" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Form.Item name="warehouse_id" label="Warehouse ID" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
                <Form.Item name="warehouse_attrs_json" label="仓库级属性 (JSON)">
                  <Input.TextArea placeholder='{"safety_stock":50,"batch_mgmt":true}' rows={4} />
                </Form.Item>
                <Button type="primary" onClick={handleSetWarehouseOverride}>设置覆盖</Button>
              </Form>
            ),
          },
          {
            key: 'effective',
            label: '生效值预览',
            children: (
              <>
                <Form form={effectiveForm} layout="vertical" style={{ maxWidth: 600 }}>
                  <Form.Item name="sku_id" label="SKU ID" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="organization_id" label="Organization ID">
                    <Input />
                  </Form.Item>
                  <Form.Item name="warehouse_id" label="Warehouse ID">
                    <Input />
                  </Form.Item>
                  <Space>
                    <Button type="primary" onClick={handleGetEffective}>查询生效值</Button>
                  </Space>
                </Form>
                {effectiveResult && (
                  <>
                    <Divider />
                    <Descriptions title="最终生效属性" column={1} bordered>
                      <Descriptions.Item label="SKU ID">{effectiveResult.master_data_id}</Descriptions.Item>
                      <Descriptions.Item label="Organization">{effectiveResult.organization_id || '(无)'}</Descriptions.Item>
                      <Descriptions.Item label="Warehouse">{effectiveResult.warehouse_id || '(无)'}</Descriptions.Item>
                      <Descriptions.Item label="生效属性">
                        {JSON.stringify(effectiveResult.effective_attrs, null, 2)}
                      </Descriptions.Item>
                    </Descriptions>
                  </>
                )}
              </>
            ),
          },
        ]}
      />
    </Card>
  )
}