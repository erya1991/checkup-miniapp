export interface ReportCard {
  id: string; health_profile_id: string; hospital_name: string | null; examination_date: string
  examination_time: string | null; report_no: string | null; report_category: string | null
  item_count: number; abnormal_count: number
}
export interface ReportResult {
  id: string; sequence_no: number; metric_name: string; result_text: string
  unit_original: string | null; unit_normalized: string | null; reference_text: string | null
  abnormal: string | null; standard_metric: null | { id: string; code: string; name: string }
}
export interface ReportDetail extends ReportCard {
  health_profile: { id: string; display_name: string }; results: ReportResult[]
}
export interface ReportPage { items: ReportCard[]; page: number; page_size: number; total: number; has_more: boolean }
export function reportsPath(profileId: string, page = 1) {
  return `/reports?health_profile_id=${encodeURIComponent(profileId)}&page=${page}&page_size=20`
}
export function reportDestination(id: string) { return `/pages/report-detail/index?id=${encodeURIComponent(id)}` }
export function abnormalLabel(value: string | null): string {
  return value === 'HIGH' ? '↑' : value === 'LOW' ? '↓' : !value || value === 'NORMAL' ? '' : '异常标记'
}
export function unfinished(status: string) {
  return ['UPLOADING', 'READY', 'QUEUED', 'PROCESSING', 'OCR_FAILED', 'PENDING_CONFIRMATION'].includes(status)
}

export interface DuplicatePrompt {
  candidates: Array<{ report_id: string; hospital_name: string | null; examination_date: string; report_no: string | null }>
  acknowledgement: string
}
export async function migrateWithConfirmation<T>(
  send: (body: { health_profile_id: string; duplicate_acknowledgement: string | null }) => Promise<T>,
  target: string,
  confirm: (prompt: DuplicatePrompt) => Promise<boolean>,
): Promise<T | null> {
  let acknowledgement: string | null = null
  for (;;) {
    try { return await send({ health_profile_id: target, duplicate_acknowledgement: acknowledgement }) }
    catch (error) {
      const failure = error as { code?: string; details?: DuplicatePrompt }
      if (failure.code !== 'DUPLICATE_CONFIRM_REQUIRED' || !failure.details) throw error
      if (!await confirm(failure.details)) return null
      acknowledgement = failure.details.acknowledgement
    }
  }
}
export function mergeReportPage(current: ReportCard[], next: ReportCard[], append: boolean) {
  return append ? [...current, ...next] : next
}
export const deletedReportDestination = '/pages/reports/index'
