import { useState, useEffect, useMemo } from 'react'
import { Card, Typography, Select, DatePicker, Space, Alert, Spin, Row, Col, Statistic } from 'antd'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'

import { client } from '@/api/client'

const { Title, Paragraph } = Typography
const { RangePicker } = DatePicker

interface GroupReportResponse {
  enterprise_id: string
  dimension: string
  summary: Record<string, number>
  is_delayed: boolean
  organization_count: number
}


const DIMENSIONS = [
  { value: 'sales', label: '销售额' },
  { value: 'purchase', label: '采购额' },
  { value: 'inventory', label: '库存' },
  { value: 'funds', label: '资金' },
  { value: 'customer', label: '客户' },
  { value: 'supplier', label: '供应商' },
]

export default function GroupReport() {
  const [dimension, setDimension] = useState<string>('sales')
  const [enterpriseId, setEnterpriseId] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [report, setReport] = useState<GroupReportResponse | null>(null)


  const fetchReport = async () => {
    if (!enterpriseId) return
    setLoading(true)
    try {
      const response = await client.get<GroupReportResponse>(
        `/group/reports/${dimension}`,
        { params: { enterprise_id: enterpriseId } },
      )
      setReport(response.data)
    } catch {
      setReport(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (enterpriseId) {
      fetchReport()
    }
  }, [dimension, enterpriseId])

  const barOption: EChartsOption = useMemo(() => {
    if (!report) return {}
    const keys = Object.keys(report.summary)
    return {
      title: { text: `${DIMENSIONS.find(d => d.value === dimension)?.label || dimension} 汇总`, left: 'center' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: keys },
      yAxis: { type: 'value' },
      series: [
        {
          name: dimension,
          type: 'bar',
          data: keys.map(k => report.summary[k]),
          itemStyle: { color: '#1890ff' },
        },
      ],
    }
  }, [report, dimension])

  const pieOption: EChartsOption = useMemo(() => {
    if (!report) return {}
    const keys = Object.keys(report.summary)
    return {
      title: { text: '维度占比', left: 'center' },
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      series: [
        {
          name: dimension,
          type: 'pie',
          radius: '60%',
          data: keys.map(k => ({ name: k, value: report.summary[k] })),
        },
      ],
    }
  }, [report, dimension])

  return (
    <Card>
      <Title level={3}>集团报表 - 跨公司汇总</Title>
      <Paragraph>
        集团管理员可查看旗下所有子公司的汇总数据：集团销售额、采购额、库存、库存金额、客户、供应商、资金。
        集团权限为只读，不可修改子公司业务单据。
      </Paragraph>

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="选择 Enterprise ID"
          style={{ width: 300 }}
          value={enterpriseId || undefined}
          onChange={setEnterpriseId}
          showSearch
        />
        <Select
          value={dimension}
          onChange={setDimension}
          style={{ width: 150 }}
          options={DIMENSIONS}
        />
        <RangePicker />
        <button
          onClick={fetchReport}
          style={{
            padding: '4px 15px',
            border: '1px solid #d9d9d9',
            borderRadius: 6,
            background: '#fff',
            cursor: 'pointer',
          }}
        >
          刷新
        </button>
      </Space>

      {report?.is_delayed && (
        <Alert
          type="warning"
          message="数据可能延迟"
          description="汇总数据与源数据延迟超过 5 分钟，建议稍后刷新"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Spin spinning={loading}>
      {report && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Statistic
                title="子公司数量"
                value={report.organization_count}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="汇总项数"
                value={Object.keys(report.summary).length}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="数据状态"
                value={report.is_delayed ? '延迟' : '正常'}
                valueStyle={{ color: report.is_delayed ? '#faad14' : '#52c41a' }}
              />
            </Col>
            <Col span={6}>
              <Statistic
                title="维度"
                value={DIMENSIONS.find(d => d.value === report.dimension)?.label || report.dimension}
              />
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Card title="汇总柱状图" bordered={false}>
                <ReactECharts option={barOption} style={{ height: 350 }} />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="维度占比" bordered={false}>
                <ReactECharts option={pieOption} style={{ height: 350 }} />
              </Card>
            </Col>
          </Row>
        </>
      )}
      </Spin>
    </Card>
  )
}
