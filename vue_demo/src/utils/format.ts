export function formatTime(value?: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

export function userStatusLabel(status?: string | null) {
  if (!status || status === 'active') return '正常'
  return status
}
