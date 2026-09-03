import { useState, useEffect } from 'react'
import { Card, Form, Input, Button, Space, Row, Col, Statistic, Table } from 'antd'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { accountingApi } from '@/api/fin/accounting'
import { formatMoney } from '@/utils/finMoney'

export default function AccountingReportsPage() {
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchData = async (params?: any) => {
    setLoading(true)
    try {
      const res = await accountingApi.reports(params)
      setReport(res.data)
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

  const revenueOption: EChartsOption = {
    title: { text: '收入vs支出', left: 'center' },
    tooltip: { trigger: 'axis' },
    legend: { data: ['收入', '支出'], top: 30 },
    xAxis: { type: 'category', data: report?.periods || [] },
    yAxis: { type: 'value' },
    series: [
      { name: '收入', type: 'bar', data: report?.revenue_series || [], itemStyle: { color: '#52c41a' } },
      { name: '支出', type: 'bar', data: report?.expense_series || [], itemStyle: { color: '#ff4d4f' } },
    ],
  }

  const profitOption: EChartsOption = {
    title: { text: '利润趋势', left: 'center' },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: report?.periods || [] },
    yAxis: { type: 'value' },
    series: [
      { name: '利润', type: 'line', data: report?.profit_series || [], smooth: true, itemStyle: { color: '#1890ff' }, areaStyle: {} },
    ],
  }

  const columns = [
    { title: '项目', dataIndex: 'item', key: 'item' },
    { title: '本期金额', dataIndex: 'current_amount', key: 'current_amount', render: (v: string) => formatMoney(v, report?.currency || 'CNY') },
    { title: '上期金额', dataIndex: 'previous_amount', key: 'previous_amount', render: (v: string) => formatMoney(v, report?.currency || 'CNY') },
    { title: '同比', dataIndex: 'yoy', key: 'yoy', render: (v: number) => `${(v * 100).toFixed(2)}%` },
  ]

  return (
    <Card title="财务报表">
      <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="period" label="账期">
          <Input placeholder="YYYY-MM" allowClear />
        </Form.Item>
        <Form.Item name="report_type" label="报表类型">
          <Input placeholder="P&L / BS / CF" allowClear />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSearch}>查询</Button>
          </Space>
        </Form.Item>
      </Form>
      {report && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}><Statistic title="本期收入" value={formatMoney(report.total_revenue, report.currency)} /></Col>
            <Col span={8}><Statistic title="本期支出" value={formatMoney(report.total_expense, report.currency)} /></Col>
            <Col span={8}><Statistic title="本期利润" value={formatMoney(report.total_profit, report.currency)} valueStyle={{ color: '#52c41a' }} /></Col>
          </Row>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={12}><Card title="收支对比" bordered={false}><ReactECharts option={revenueOption} style={{ height: 350 }} /></Card></Col>
            <Col span={12}><Card title="利润趋势" bordered={false}><ReactECharts option={profitOption} style={{ height: 350 }} /></Card></Col>
          </Row>
          <Table columns={columns} dataSource={report.items || []} rowKey="item" loading={loading} pagination={false} />
        </>
      )}
    </Card>
  )
}