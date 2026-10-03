export interface MetricIdentity { id: string; code: string; name: string }
export interface MetricHistoryItem {
  lab_result_id: string; report_id: string; metric_name: string; result_text: string
  result_numeric: number | null; comparator: string | null
  unit_original: string | null; unit_normalized: string | null; unit: string | null
  reference_text: string | null; abnormal: string | null
  examination_date: string; examination_time: string | null
  hospital_name: string | null; report_no: string | null
}
export interface MetricCard {
  standard_metric: MetricIdentity; is_favorite: boolean; latest: MetricHistoryItem
  history_count: number; trend_plottable_count: number; trend_series_count: number
}
export interface PageResult<T> { items: T[]; page: number; page_size: number; total: number; has_more: boolean }
export interface TrendPoint {
  lab_result_id: string; report_id: string; examination_date: string; examination_time: string | null
  value: number; result_text: string; unit: string | null; reference_text: string | null; abnormal: string | null
}
export interface TrendSeries { series_key: string; unit: string | null; points: TrendPoint[] }
export interface MetricTrend { standard_metric: MetricIdentity; history_count: number; plottable_count: number; series: TrendSeries[] }
export function metricsPath(profileId: string, page = 1) {
  return `/profile-metrics?health_profile_id=${encodeURIComponent(profileId)}&page=${page}&page_size=20`
}
export function metricPath(profileId: string, metricId: string, kind: '' | 'history' | 'trend' = '', page = 1) {
  const base = `/profile-metrics/${encodeURIComponent(metricId)}${kind ? '/' + kind : ''}?health_profile_id=${encodeURIComponent(profileId)}`
  return kind === 'history' ? `${base}&page=${page}&page_size=50` : base
}
export function favoritePath(profileId: string, metricId: string) {
  return `/favorites/${encodeURIComponent(metricId)}?health_profile_id=${encodeURIComponent(profileId)}`
}
export function metricDestination(metricId: string) {
  return `/pages/metric-detail/index?id=${encodeURIComponent(metricId)}`
}
export function mergePage<T>(current: T[], incoming: T[], append: boolean) {
  return append ? [...current, ...incoming] : incoming
}
export function defaultSeries(series: TrendSeries[]) { return series[0]?.series_key || '' }
export function selectedSeries(series: TrendSeries[], key: string) {
  return series.find(item => item.series_key === key) || null
}
export function examinationLabel(result: { examination_date: string; examination_time: string | null }) {
  return `${result.examination_date}${result.examination_time ? ' ' + result.examination_time : '（时间未记录）'}`
}
export function chartDateLabel(result: { examination_date: string; examination_time: string | null }) {
  return { year: result.examination_date.slice(0, 4), date: result.examination_date.slice(5),
    time: result.examination_time?.slice(0, 5) || '' }
}
export const emptyTrendMessage = '暂无可绘制数值趋势，历史结果仍可查看。'

// Page-local request lifecycle, including profile changes while requests are pending.
export function requestGuard() {
  let version = 0
  return { next: () => ++version, invalidate: () => { ++version }, current: (run: number) => run === version }
}

export async function changeFavorite(
  send: (method: 'PUT' | 'DELETE') => Promise<{ is_favorite: boolean }>, current: boolean,
) { return (await send(current ? 'DELETE' : 'PUT')).is_favorite }

// Geometry only: keep every server point, including identical dates/values.
export function chartGeometry(points: TrendPoint[]) {
  const width = Math.max(320, 96 + Math.max(0, points.length - 1) * 84)
  if (!points.length) return { width, min: 0, max: 0, dots: [], lines: [] }
  const values = points.map(point => Number(point.value))
  const min = Math.min(...values), max = Math.max(...values)
  const span = max - min || Math.max(Math.abs(max) * 0.1, 1)
  const low = min - span * 0.1, high = max + span * 0.1
  const dots = points.map((point, index) => ({
    point, x: points.length === 1 ? width / 2 : 48 + index * (width - 96) / (points.length - 1),
    y: 190 - (Number(point.value) - low) / (high - low) * 160,
  }))
  const lines = dots.slice(1).map((dot, index) => {
    const previous = dots[index], dx = dot.x - previous.x, dy = dot.y - previous.y
    return { id: dot.point.lab_result_id, x: previous.x, y: previous.y,
      width: Math.sqrt(dx * dx + dy * dy), angle: Math.atan2(dy, dx) * 180 / Math.PI }
  })
  return { width, min, max, dots, lines }
}

export function appFontSize(info: { fontSizeSetting?: number; hostFontSizeSetting?: number }) {
  return info.fontSizeSetting || info.hostFontSizeSetting || 16
}
