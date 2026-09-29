import { apiBaseUrl } from './config'

export interface Profile {
  id: string; display_name: string; relation: string; gender: string | null; birth_date: string | null
}
export interface Asset { id: string; page_no: number; mime_type: string; file_size: number; upload_status: string }
export interface OcrCounts { total_count: number; auto_count: number; review_count: number }
export interface Ingestion {
  id: string; health_profile_id: string; status: string; created_at: string; assets: Asset[]
  result_summary?: OcrCounts | null
}
export interface OcrStatus {
  ingestion_status: string
  task: null | {
    id: string; run_no: number; status: string; attempt_count: number
    started_at: string | null; finished_at: string | null
    result_summary: null | OcrCounts
    error_code: string | null
  }
}
export interface UploadAuthorization {
  object_key: string; bucket: string; region: string; start_time: number; expired_time: number
  credentials: { tmpSecretId: string; tmpSecretKey: string; sessionToken: string }
}

export class ApiError extends Error {
  constructor(public status: number, public code: string) { super(code) }
}

export function token() { return uni.getStorageSync('authToken') as string || '' }
export function clearToken() { uni.removeStorageSync('authToken') }

export async function request<T>(path: string, method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET', data?: Record<string, unknown>): Promise<T> {
  const response = await uni.request({
    url: `${apiBaseUrl}${path}`, method, data,
    header: token() ? { Authorization: `Bearer ${token()}` } : {},
  })
  if (response.statusCode < 200 || response.statusCode >= 300) {
    const body = response.data as { code?: string }
    if (response.statusCode === 401) clearToken()
    throw new ApiError(response.statusCode, body?.code || 'REQUEST_FAILED')
  }
  return response.data as T
}

export async function ensureLogin(): Promise<{ id: string; default_health_profile_id: string | null }> {
  if (token()) {
    try { return await request('/me') } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error
    }
  }
  const login = await uni.login({ provider: 'weixin' })
  if (!login.code) throw new Error('WECHAT_LOGIN_FAILED')
  const auth = await request<{ access_token: string }>('/auth/wechat', 'POST', { code: login.code })
  uni.setStorageSync('authToken', auth.access_token)
  return request('/me')
}
