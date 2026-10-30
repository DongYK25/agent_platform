export interface Option {
  value: string
  label: string
}

export const workOrderStatuses: Option[] = [
  { value: 'pending', label: '待处理' },
  { value: 'processing', label: '处理中' },
  { value: 'done', label: '已完成' },
]

export const priorities: Option[] = [
  { value: 'low', label: '低' },
  { value: 'medium', label: '中' },
  { value: 'high', label: '高' },
]

export function labelOf(options: Option[], value?: string | null) {
  if (!value) return '—'
  return options.find((item) => item.value === value)?.label ?? value
}
