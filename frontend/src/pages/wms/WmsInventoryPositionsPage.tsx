import { useState } from 'react'
import { Card, Table, Form, Input, Select, Button, Tag, Row, Col, Space } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { wmsApi } from '@/api/wms'
import type { InventoryPosition, InventoryStatus } from '@/types/wms'

const STATUS_OPTIONS: InventoryStatus[] = ['available', 'frozen', 'inspection', 'blocked']

const statusColorMap: Record<string, string> = {
  available: 'green', frozen: 'blue', inspection: 'orange', blocked: 'red',
}

export default function WmsInventoryPositionsPage() {
  const [positions, setPositions] = useState<InventoryPosition[]>([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const handleSearch = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (values.sku_id) params.sku_id = values.sku_id
      if (values.location_id) params.location_id = values.location_id
      if (values.warehouse_id) params.warehouse_id = values.warehouse_id
      if (values.inventory_status) params.inventory_status = values.inventory_status
      const data = await wmsApi.positions.query(params)
      setPositions(data)
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    form.resetFields()
    setPositions([])
  }

  const columns = [
    { title: 'SKU', dataIndex: 'sku_id', key: 'sku_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '库位', dataIndex: 'location_id', key: 'location_id', render: (v: string) => v.substring(0, 8) + '...' },
    { title: '批次', dataIndex: 'batch_number', key: 'batch_number' },
    { title: '序列号', dataIndex: 'serial_number', key: 'serial_number' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity', render: (v: number) => <Tag color={v > 0 ? 'green' : 'red'}>{v}</Tag> },
    {
      title: '状态',
      dataIndex: 'inventory_status',
      key: 'inventory_status',
      render: (v: string) => <Tag color={statusColorMap[v] || 'default'}>{v}</Tag>,
    },
    { title: '过期日期', dataIndex: 'expiry_date', key: 'expiry_date' },
    { title: '最后更新', dataIndex: 'last_updated_at', key: 'last_updated_at' },
  ]

  const heatmapOption = {
    tooltip: { position: 'top' as const },
    grid: { height: '60%', top: '10%' },
    xAxis: { type: 'category' as const, data: [...new Set(positions.map((p) => p.location_id.substring(0, 8)))], splitArea: { show: true } },
    yAxis: { type: 'category' as const, data: [...new Set(positions.map((p) => p.sku_id.substring(0, 8)))], splitArea: { show: true } },
    visualMap: {
      min: 0,
      max: Math.max(...positions.map((p) => p.quantity), 1),
      calculable: true,
      orient: 'horizontal' as const,
      left: 'center',
      bottom: '5%',
    },
    series: [
      {
        name: '库存分布',
        type: 'heatmap' as const,
        data: positions.map((p) => [p.location_id.substring(0, 8), p.sku_id.substring(0, 8), p.quantity]),
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } },
      },
    ],
  }

  return (
    <Card>
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="sku_id" label="SKU ID">
          <Input placeholder="按 SKU 查询" allowClear />
        </Form.Item>
        <Form.Item name="location_id" label="库位 ID">
          <Input placeholder="按库位查询" allowClear />
        </Form.Item>
        <Form.Item name="warehouse_id" label="仓库 ID">
          <Input placeholder="按仓库查询" allowClear />
        </Form.Item>
        <Form.Item name="inventory_status" label="状态">
          <Select placeholder="全部" allowClear style={{ width: 120 }} options={STATUS_OPTIONS.map((s) => ({ label: s, value: s }))} />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>查询</Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>

      <Row gutter={16}>
        <Col span={10}>
          <Card title="库位分布热力图" size="small">
            {positions.length > 0 ? (
              <ReactECharts option={heatmapOption} style={{ height: 400 }} />
            ) : (
              <Tag>请先查询数据</Tag>
            )}
          </Card>
        </Col>
        <Col span={14}>
          <Table
            columns={columns}
            dataSource={positions}
            rowKey="position_id"
            loading={loading}
            pagination={{ pageSize: 20 }}
            size="small"
          />
        </Col>
      </Row>
    </Card>
  )
}
