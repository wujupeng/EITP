import { useState, useEffect } from 'react'
import { Card, Table, Form, Input, Button, Space, Row, Col } from 'antd'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { accountingApi } from '@/api/fin/accounting'
import { formatMoney } from '@/utils/finMoney'

const AGING_BUCKETS = ['0-30', '31-60', '61-90', '91-180', '180+']

export default function AgingAnalysisPage() {
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await accountingApi.agingAnalysis(params)
      setData(res.data?.items || [])
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleSearch = async () => {
    const values = await form.validateFields()
    fetchData(values)
  }

  const handleReset = () => {
    form.resetFields()
    fetchData()
  }

  const barOption: EChartsOption = {
    title: { text: '账龄分布', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: AGING_BUCKETS },
    yAxis: { type: 'value' },
    series: [
      {
        name: '应收金额',
        type: 'bar',
        data: AGING_BUCKETS.map(bucket => {
          const item = data.find(d => d.bucket === bucket)
          return item ? Number(item.amount) : 0
        }),
        itemStyle: { color: '#1890ff' },
      },
    ],
  }

  const columns = [
    { title: '客户', dataIndex: 'customer', key: 'customer' },
    { title: '账龄区间', dataIndex: 'bucket', key: 'bucket' },
    { title: '应收金额', dataIndex: 'amount', key: 'amount', render: (v: string, record: any) => formatMoney(v, record.currency) },
    { title: '占比', dataIndex: 'ratio', key: 'ratio', render: (v: number) => `${(v * 100).toFixed(2)}%` },
  ]

  return (
    <Card title="账龄分析">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="customer" label="客户">
          <Input placeholder="客户" allowClear />
        </Form.Item>
        <Form.Item name="period" label="账期">
          <Input placeholder="YYYY-MM" allowClear />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </Form.Item>
      </Form>
      <Row gutter={16}>
        <Col span={12}>
          <Card title="账龄柱状图" size="small">
            <ReactECharts option={barOption} style={{ height: 400 }} />
          </Card>
        </Col>
        <Col span={12}>
          <Table columns={columns} dataSource={data} rowKey="customer" loading={loading} pagination={{ pageSize: 20 }} size="small" />
        </Col>
      </Row>
    </Card>
  )
}