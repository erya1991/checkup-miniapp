export type AdminTagType = 'success' | 'info' | 'warning' | 'danger'

const statuses: Record<string, { label: string; type: AdminTagType }> = {
  ACTIVE: { label: '启用 · ACTIVE', type: 'success' },
  INACTIVE: { label: '停用 · INACTIVE', type: 'info' },
  QUEUED: { label: '等待 · QUEUED', type: 'info' },
  PROCESSING: { label: '处理中 · PROCESSING', type: 'warning' },
  SUCCEEDED: { label: '完成 · SUCCEEDED', type: 'success' },
  FAILED: { label: '失败 · FAILED', type: 'danger' },
}

export function adminStatus(status: string) {
  return statuses[status] || { label: status || '—', type: 'info' as const }
}

export function activeAdminMenu(path: string) {
  return path.startsWith('/standard-metrics/') ? '/standard-metrics' : path
}
