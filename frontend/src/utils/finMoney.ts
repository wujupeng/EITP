const CURRENCY_SYMBOLS: Record<string, string> = {
  CNY: '¥',
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
  HKD: 'HK$',
}

export function formatMoney(amount: string | number, currency: string = 'CNY'): string {
  const symbol = CURRENCY_SYMBOLS[currency] || currency
  const str = String(amount ?? '').trim()
  if (str === '' || str === '-') return '-'
  const negative = str.startsWith('-')
  const digits = str.replace(/[^0-9.]/g, '')
  if (digits === '' || digits === '.') return `${symbol}0.00`
  const parts = digits.split('.')
  const intPart = parts[0] || '0'
  const decPart = parts[1] || ''
  const intFormatted = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
  const dec = decPart.padEnd(2, '0').substring(0, 2)
  return `${negative ? '-' : ''}${symbol}${intFormatted}.${dec}`
}

export function parseMoney(str: string): string {
  if (!str) return '0'
  const cleaned = str.replace(/[^0-9.\-]/g, '')
  if (cleaned === '' || cleaned === '-' || cleaned === '.') return '0'
  const negative = cleaned.startsWith('-')
  const positive = negative ? cleaned.substring(1) : cleaned
  const parts = positive.split('.')
  const intPart = parts[0] || '0'
  const decPart = parts[1] || ''
  const dec = decPart.substring(0, 2)
  const sign = negative ? '-' : ''
  return dec ? `${sign}${intPart}.${dec}` : `${sign}${intPart}`
}

export function moneyToNumber(amount: string): number {
  const parsed = parseMoney(amount)
  return Number(parsed)
}