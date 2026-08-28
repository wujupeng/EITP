import { Card, Typography } from 'antd'

const { Title, Paragraph } = Typography

export default function Operations() {
  return (
    <Card>
      <Title level={3}>业务操作 - 进销存</Title>
      <Paragraph>
        采购、销售、库存、仓库管理等日常业务操作。功能模块由租户级功能开关控制。
      </Paragraph>
      <Paragraph type="secondary">
        T06 阶段将实现：租户级业务规则、审批流、定价、税务、库存策略。
      </Paragraph>
    </Card>
  )
}