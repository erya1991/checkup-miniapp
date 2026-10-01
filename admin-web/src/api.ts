import { setToken, token } from './auth'

export interface Metric {
  id: string; code: string; name: string; category: string | null; status: string
  alias_count: number; formal_result_count: number; pending_confirmation_count: number
  created_at: string; updated_at: string
}
export interface Alias {
  id: string; standard_metric_id: string; alias: string; normalized_alias: string
  alias_type: string; status: string; metric_code: string; metric_name: string
}
export interface Page<T> { items: T[]; total: number; page: number; page_size: number }
export interface Issue {
  issue_type: string; representative_name?: string; normalized_name?: string; sample_names?: string[]
  ocr_code?: string; ocr_standard_name?: string; standard_metric_id?: string
  occurrence_count: number; ingestion_count: number; latest_seen_at: string
}
export interface Task {
  id: string; ingestion_id: string; run_no: number; status: string; pipeline_version: string | null
  attempt_count: number; created_at: string; started_at: string | null; finished_at: string | null
  last_error_code: string | null; result_summary: { total_count?: number; auto_count?: number; review_count?: number }
}

const messages: Record<string, string> = {
  ADMIN_AUTH_REQUIRED: '请登录管理员账号', ADMIN_AUTH_INVALID: '凭据错误或登录已失效，请重新登录',
  ADMIN_AUTH_NOT_CONFIGURED: '服务端尚未配置有效管理员凭据',
  STANDARD_METRIC_CODE_CONFLICT: 'code 已存在，请使用其它 code',
  STANDARD_METRIC_CODE_IMMUTABLE: '创建后不能修改 code',
  STANDARD_METRIC_IN_USE_BY_PENDING_CONFIRMATION: '该指标仍被待确认工作区引用，暂时不能停用',
  STANDARD_METRIC_NOT_FOUND: '标准指标不存在', METRIC_ALIAS_NOT_FOUND: '别名不存在',
  METRIC_ALIAS_DUPLICATE: '归一化后的 ACTIVE 别名已存在',
  METRIC_ALIAS_CONFLICT: '名称与 ACTIVE 标准指标或别名冲突；与目标自身 code/name 等价的别名也不能创建',
  METRIC_ALIAS_TARGET_INACTIVE: '目标标准指标已停用，请先恢复或选择其它指标',
  METRIC_ALIAS_TARGET_IMMUTABLE: '别名目标创建后只读；请停用旧别名后新建',
  INVALID_ADMIN_INPUT: '请检查必填项、字段长度和允许的状态',
  INVALID_STANDARD_METRIC: 'code / name 不能为空，且需满足长度限制',
  INVALID_METRIC_ALIAS: '别名不能为空或仅包含分隔符，请检查字段和类型',
}
export class ApiError extends Error {
  constructor(public code: string, public details: Record<string, unknown> = {}) {
    super(messages[code] || `请求失败：${code}`)
    if (typeof details.pending_count === 'number') this.message += `（引用 ${details.pending_count} 项）`
  }
}
export function errorText(error: unknown) { return error instanceof Error ? error.message : '请求失败，请重试' }
export function query(values: Record<string, string | number | undefined>) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) if (value !== undefined && value !== '') params.set(key, String(value))
  return params.toString()
}
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  if (token.value) headers.set('Authorization', `Bearer ${token.value}`)
  let response: Response
  try { response = await fetch(`/api/v1/admin${path}`, { ...options, headers }) }
  catch { throw new Error('无法连接服务，请检查网络后重试') }
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/login') {
      setToken('')
      window.dispatchEvent(new Event('admin-session-expired'))
    }
    throw new ApiError(data.code || `HTTP_${response.status}`, data.details)
  }
  return data as T
}
export function save<T>(path: string, value: unknown, method = 'POST') {
  return request<T>(path, { method, body: JSON.stringify(value) })
}
