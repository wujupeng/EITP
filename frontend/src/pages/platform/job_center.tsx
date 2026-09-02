import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Tabs } from 'antd'
import { pltApi } from '@/api/platform'

export default function JobCenterPage() {
  const [jobs, setJobs] = useState<any[]>([])
  const [executions, setExecutions] = useState<any[]>([])

  useEffect(() => {
    pltApi.job.definitions().then(resp => setJobs(resp.data.items || []))
    pltApi.job.executions().then(resp => setExecutions(resp.data.items || []))
  }, [])

  return (
    <Card title="Job Center">
      <Tabs items={[
        { key: 'defs', label: '任务定义', children: (
          <Table dataSource={jobs} rowKey="job_id" columns={[
            { title: '任务名称', dataIndex: 'job_name' },
            { title: 'Cron', dataIndex: 'cron_expression' },
            { title: '状态', dataIndex: 'enabled', render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '启用' : '禁用'}</Tag> },
            { title: '操作', render: (_, r: any) => <Button size="small" onClick={() => pltApi.job.execute(r.job_id)}>执行</Button> },
          ]} />
        )},
        { key: 'execs', label: '执行记录', children: (
          <Table dataSource={executions} rowKey="execution_id" columns={[
            { title: '执行ID', dataIndex: 'execution_id' },
            { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'SUCCESS' ? 'green' : v === 'FAILED' ? 'red' : 'blue'}>{v}</Tag> },
            { title: '耗时(ms)', dataIndex: 'duration_ms' },
            { title: '开始时间', dataIndex: 'started_at' },
          ]} />
        )},
      ]} />
    </Card>
  )
}