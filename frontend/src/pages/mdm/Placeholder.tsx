import { Card, Typography } from 'antd'

const { Title, Paragraph } = Typography

interface PlaceholderProps {
  title: string
  description: string
}

export default function MdmPlaceholder({ title, description }: PlaceholderProps) {
  return (
    <Card>
      <Title level={3}>{title}</Title>
      <Paragraph type="secondary">{description}</Paragraph>
      <Paragraph type="secondary">该页面将在 T15 任务中实现完整功能。</Paragraph>
    </Card>
  )
}