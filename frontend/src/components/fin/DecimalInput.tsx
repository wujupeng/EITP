import { Input } from 'antd'
import type { InputProps } from 'antd'
import type { ChangeEvent } from 'react'
import { parseMoney } from '@/utils/finMoney'

interface DecimalInputProps extends Omit<InputProps, 'value' | 'onChange'> {
  value?: string
  onChange?: (value: string) => void
}

export default function DecimalInput({ value, onChange, ...rest }: DecimalInputProps) {
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    onChange?.(parseMoney(e.target.value))
  }
  return <Input value={value} onChange={handleChange} {...rest} />
}