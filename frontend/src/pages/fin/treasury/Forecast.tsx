import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Space, Row, Col, Statistic, Table } from 'antd'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { treasuryApi } from '@/api/fin/treasury'
import { formatMoney } from '@/utils/finMoney'

export default function TreasuryForecastPage() {
  const [forecast, setForecast] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await treasuryApi.forecast(params)
      setForecast(res.data)
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

  const lineOption: EChartsOption = {
    title: { text: '资金流入流出预测', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['流入', '流出', '净额'], top: 30 },
    xAxis: { type: 'category', data: forecast?.periods || [] },
    yAxis: { type: 'value' },
    series: [
      { name: '流入', type: 'line', data: forecast?.inflow_series || [], smooth: true, itemStyle: { color: '#52c41a' } },
      { name: '流出', type: 'line', data: forecast?.outflow_series || [], smooth: true, itemStyle: { color: '#ff4d4f' } },
      { name: '净额', type: 'line', data: forecast?.net_series || [], smooth: true, itemStyle: { color: '#1890ff' }, areaStyle: {} },
    ],
  }

  const columns = [
    { title: '期间', dataIndex: 'period', key: 'period' },
    { title: '预计流入', dataIndex: 'inflow', key: 'inflow', render: (v: string) => formatMoney(v, forecast?.currency || 'CNY') },
    { title: '预计流出', dataIndex: 'outflow', key: 'outflow', render: (v: string) => formatMoney(v, forecast?.currency || 'CNY') },
    { title: '净额', dataIndex: 'net', key: 'net', render: (v: string) => formatMoney(v, forecast?.currency || 'CNY') },
    { title: '期末余额预测', dataIndex: 'end_balance', key: 'end_balance', render: (v: string) => formatMoney(v, forecast?.currency || 'CNY') },
  ]

  return (
    <Card title="资金预测">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="horizon" label="预测周期">
          <Input placeholder="30/60/90 天" allowClear />
        </Form.Item>
        <Form.Item name="currency" label="币种">
          <Input placeholder="CNY" allowClear />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>预测</Button>
          </Space>
        </Form.Item>
      </Form>
      {forecast && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}><Statistic title="预计总流入" value={formatMoney(forecast.total_inflow, forecast.currency)} valueStyle={{ color: '#52c41a' }} /></Col>
            <Col span={8}><Statistic title="预计总流出" value={formatMoney(forecast.total_outflow, forecast.currency)} valueStyle={{ color: '#ff4d4f' }} /></Col>
            <Col span={8}><Statistic title="预计净额" value={formatMoney(forecast.total_net, forecast.currency)} /></Col>
          </Row>
          <Card title="资金预测趋势" bordered={false} style={{ marginBottom: 16 }}>
            <ReactECharts option={lineOption} style={{ height: 400 }} />
          </Card>
          <Table columns={columns} dataSource={forecast.details || []} rowKey="period" loading={loading} pagination={false} />
        </>
      )}
    </Card>
  )
}