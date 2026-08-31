import { Card, Typography } from 'antd'

const { Title, Paragraph } = Typography

interface WmsPlaceholderProps {
  title: string
  description: string
  permission?: string
}

export default function WmsPlaceholder({ title, description, permission }: WmsPlaceholderProps) {
  return (
    <Card>
      <Title level={3}>{title}</Title>
      <Paragraph type="secondary">{description}</Paragraph>
      {permission && (
        <Paragraph type="secondary">所需权限: <code>{permission}</code></Paragraph>
      )}
      <Paragraph type="secondary">该页面将在 T15 任务中实现完整功能。</Paragraph>
    </Card>
  )
}