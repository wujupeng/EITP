import { useState } from 'react'
import { Card, Form, Select, Button, Input, message, Tabs } from 'antd'
import { prodApi } from '@/api/prod'

const ITEMS = [
  { label: 'V01 性能基线', value: 'V01_BASELINE' },
  { label: 'V02 并发用户', value: 'V02_CONCURRENT' },
  { label: 'V03 连接池压力', value: 'V03_CONNPOOL' },
  { label: 'V04 Redis缓存防护', value: 'V04_CACHE' },
  { label: 'V05 Outbox堆积恢复', value: 'V05_OUTBOX' },
  { label: 'V06 Saga补偿', value: 'V06_SAGA' },
  { label: 'V07 Job恢复', value: 'V07_JOB' },
  { label: 'V08 告警验证', value: 'V08_ALERT' },
  { label: 'V09 Trace全链路', value: 'V09_TRACE' },
  { label: 'V10 备份恢复', value: 'V10_BACKUP' },
  { label: 'V11 灾备演练', value: 'V11_DR' },
  { label: 'V12 容器重启', value: 'V12_CONTAINER' },
  { label: 'V13 限流验证', value: 'V13_RATELIMIT' },
  { label: 'V14 大租户容量', value: 'V14_LARGE_TENANT' },
  { label: 'V15 全平台回归', value: 'V15_REGRESSION' },
  { label: 'V16 SEC重认证', value: 'V16_SEC_RECERT' },
]

export default function ProdExecutePage() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  const onExecute = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      const resp = await prodApi.verification.execute(values)
      message.success(`验证已提交: ${resp.data.run_id}`)
    } catch {
      message.error('验证提交失败')
    } finally {
      setLoading(false)
    }
  }

  const onBatch = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      const resp = await prodApi.verification.executeBatch({
        items: ITEMS.map(i => i.value),
        executor: values.executor,
        environment: values.environment,
        tenant_id: values.tenant_id,
      })
      message.success(`批量验证已提交: ${resp.data.total} 项`)
    } catch {
      message.error('批量验证提交失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="验证执行">
      <Form form={form} layout="vertical">
        <Form.Item name="verification_item" label="验证项" rules={[{ required: true }]}>
          <Select options={ITEMS} />
        </Form.Item>
        <Form.Item name="executor" label="执行人角色" rules={[{ required: true }]}>
          <Select options={[
            { label: 'SRE', value: 'SRE' },
            { label: '性能', value: 'PERF' },
            { label: 'DBA', value: 'DBA' },
            { label: '安全负责人', value: 'SEC_OFF' },
            { label: '平台管理员', value: 'PA' },
            { label: 'CI/CD', value: 'CICD' },
          ]} />
        </Form.Item>
        <Form.Item name="environment" label="执行环境" rules={[{ required: true }]}>
          <Select options={[
            { label: 'Staging', value: 'STAGING' },
            { label: 'Pre-Prod', value: 'PRE_PROD' },
          ]} />
        </Form.Item>
        <Form.Item name="tenant_id" label="租户ID" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item name="config_parameters" label="配置参数(JSON)">
          <Input.TextArea rows={4} placeholder='{}' />
        </Form.Item>
        <Button type="primary" loading={loading} onClick={onExecute}>执行单项验证</Button>
        <Button loading={loading} onClick={onBatch} style={{ marginLeft: 8 }}>批量执行(16项)</Button>
      </Form>
    </Card>
  )
}