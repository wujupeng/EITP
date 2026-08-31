import { useState } from 'react'
import { Card, Form, Input, Button, Table, Space, message, Descriptions, Tag, Tabs, Divider } from 'antd'
import { SearchOutlined, BarcodeOutlined, ReloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { masterDataQueryApi } from '@/api/mdm'
import type { MasterDataQueryResult, BarcodeLocateResult } from '@/api/mdm/types'

export default function MasterDataQuery() {
  const [results, setResults] = useState<MasterDataQueryResult[]>([])
  const [detail, setDetail] = useState<MasterDataQueryResult | null>(null)
  const [barcodeResult, setBarcodeResult] = useState<BarcodeLocateResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [queryForm] = Form.useForm()
  const [barcodeForm] = Form.useForm()

  const handleQuery = async () => {
    const values = await queryForm.validateFields()
    setLoading(true)
    try {
      const params: { enterprise_product_code?: string; group_product_id?: string; limit?: number } = {}
      if (values.enterprise_product_code) params.enterprise_product_code = values.enterprise_product_code
      if (values.group_product_id) params.group_product_id = values.group_product_id
      params.limit = values.limit || 50
      const data = await masterDataQueryApi.query(params)
      setResults(data)
    } catch {
      message.error('查询失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGetDetail = async (id: string) => {
    setLoading(true)
    try {
      const data = await masterDataQueryApi.get(id)
      setDetail(data)
    } catch {
      message.error('获取详情失败')
    } finally {
      setLoading(false)
    }
  }

  const safeStr = (v: unknown): string => (v != null ? String(v) : '-')

  const handleLocateByBarcode = async () => {
    const values = await barcodeForm.validateFields()
    setLoading(true)
    try {
      const data = await masterDataQueryApi.locateByBarcode(values.barcode)
      setBarcodeResult(data)
      message.success('条码定位成功')
    } catch {
      message.error('条码定位失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '企业商品编码',
      key: 'enterprise_product_code',
      render: (_: unknown, record: MasterDataQueryResult) => safeStr(record.enterprise_product?.enterprise_product_code),
    },
    {
      title: '企业商品名称',
      key: 'enterprise_product_name',
      render: (_: unknown, record: MasterDataQueryResult) => safeStr(record.enterprise_product?.enterprise_product_name),
    },
    {
      title: '集团商品',
      key: 'group_product_name',
      render: (_: unknown, record: MasterDataQueryResult) => safeStr(record.group_product?.group_product_name),
    },
    {
      title: 'SKU 数量',
      key: 'sku_count',
      render: (_: unknown, record: MasterDataQueryResult) => record.enterprise_skus?.length || 0,
    },
    {
      title: '是否有定制',
      key: 'has_customization',
      render: (_: unknown, record: MasterDataQueryResult) =>
        record.customization ? <Tag color="green">有</Tag> : <Tag>无</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: MasterDataQueryResult) => (
        <Button size="small" onClick={() => handleGetDetail(safeStr(record.enterprise_product?.enterprise_product_id))}>
          查看详情
        </Button>
      ),
    },
  ]

  const chartOption = {
    title: { text: '主数据分布统计', left: 'center' },
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left' },
    series: [
      {
        name: '主数据分布',
        type: 'pie',
        radius: '50%',
        data: [
          { value: results.filter((r) => r.customization).length, name: '有定制' },
          { value: results.filter((r) => !r.customization).length, name: '无定制' },
        ],
        emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
      },
    ],
  }

  return (
    <Card>
      <Tabs
        items={[
          {
            key: 'query',
            label: '主数据查询',
            children: (
              <>
                <Form form={queryForm} layout="inline" style={{ marginBottom: 16 }}>
                  <Form.Item name="enterprise_product_code" label="企业商品编码">
                    <Input placeholder="如 EP-001" />
                  </Form.Item>
                  <Form.Item name="group_product_id" label="集团商品ID">
                    <Input placeholder="集团商品 UUID" />
                  </Form.Item>
                  <Form.Item name="limit" label="限制">
                    <Input placeholder="50" />
                  </Form.Item>
                  <Form.Item>
                    <Space>
                      <Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleQuery}>
                        查询
                      </Button>
                      <Button icon={<ReloadOutlined />} onClick={() => { setResults([]); setDetail(null) }}>
                        清空
                      </Button>
                    </Space>
                  </Form.Item>
                </Form>

                {results.length > 0 && (
                  <ReactECharts option={chartOption} style={{ height: 300, marginBottom: 16 }} />
                )}

                <Table
                  columns={columns}
                  dataSource={results}
                  rowKey={(r) => safeStr(r.enterprise_product?.enterprise_product_id) || Math.random().toString()}
                  loading={loading}
                  pagination={{ pageSize: 20 }}
                />

                {detail && (
                  <>
                    <Divider>主数据详情</Divider>
                    <Descriptions bordered column={2}>
                      <Descriptions.Item label="企业商品编码">
                        {safeStr(detail.enterprise_product?.enterprise_product_code)}
                      </Descriptions.Item>
                      <Descriptions.Item label="企业商品名称">
                        {safeStr(detail.enterprise_product?.enterprise_product_name)}
                      </Descriptions.Item>
                      <Descriptions.Item label="集团商品" span={2}>
                        {detail.group_product ? JSON.stringify(detail.group_product) : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="企业 SKU" span={2}>
                        {detail.enterprise_skus?.map((s, i) => (
                          <Tag key={i}>{safeStr(s.enterprise_sku_code) || JSON.stringify(s)}</Tag>
                        ))}
                      </Descriptions.Item>
                      <Descriptions.Item label="定制信息" span={2}>
                        {detail.customization ? JSON.stringify(detail.customization) : '无定制'}
                      </Descriptions.Item>
                    </Descriptions>
                  </>
                )}
              </>
            ),
          },
          {
            key: 'barcode',
            label: '条码定位',
            children: (
              <>
                <Form form={barcodeForm} layout="inline" style={{ marginBottom: 16 }}>
                  <Form.Item name="barcode" label="条码" rules={[{ required: true }]}>
                    <Input placeholder="如 6900000000001" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" icon={<BarcodeOutlined />} loading={loading} onClick={handleLocateByBarcode}>
                      定位
                    </Button>
                  </Form.Item>
                </Form>

                {barcodeResult && (
                  <Descriptions title="条码定位结果" bordered column={2}>
                    <Descriptions.Item label="企业 SKU ID">
                      {barcodeResult.enterprise_sku_id}
                    </Descriptions.Item>
                    <Descriptions.Item label="企业 SKU 编码">
                      {barcodeResult.enterprise_sku_code || '-'}
                    </Descriptions.Item>
                    <Descriptions.Item label="企业商品 ID">
                      {barcodeResult.enterprise_product_id}
                    </Descriptions.Item>
                    <Descriptions.Item label="条码来源">
                      <Tag color="blue">{barcodeResult.barcode_source}</Tag>
                    </Descriptions.Item>
                  </Descriptions>
                )}
              </>
            ),
          },
        ]}
      />
    </Card>
  )
}
