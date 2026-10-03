import type { Ingestion } from './api'
import type { ReportCard } from './reports'
import type { MetricCard } from './profile-metrics'

const priority: Record<string, number> = { PENDING_CONFIRMATION: 0, OCR_FAILED: 1, READY: 2, UPLOADING: 3, QUEUED: 4, PROCESSING: 5 }
export function pendingSummary(ingestions: Ingestion[]) {
  const items = ingestions.filter(item => item.status in priority)
  const first = [...items].sort((a, b) => priority[a.status] - priority[b.status])[0] || null
  return { count: items.length, first }
}
export function recentReports(reports: ReportCard[]) { return reports.slice(0, 2) }
export function favoriteSummary(metrics: MetricCard[]) { return metrics.filter(item => item.is_favorite).slice(0, 3) }
