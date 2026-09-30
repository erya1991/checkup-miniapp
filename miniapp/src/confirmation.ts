export interface StandardMetric { id: string; code: string; name: string; status: string }
export interface ConfirmationItem {
  id: string; sequence_no: number; metric_name: string; result_text: string
  unit_original: string | null; reference_text: string | null; standard_metric_id: string | null
  unit_normalized?: string | null
  source_type: 'OCR_AUTO' | 'OCR_CORRECTED' | 'MANUAL'
  review_status: 'PENDING' | 'RESOLVED'; resolution: string | null
  source: null | { asset_id: string; page_no: number; final_decision: string; review_reasons: string[] }
}

export async function saveThenCommit<T>(save: () => Promise<void>, commit: () => Promise<T>): Promise<T> {
  try { await save() }
  catch (e) {
    // A previous commit may have succeeded even though its response was lost.
    if (!(typeof e === 'object' && e !== null && 'code' in e && e.code === 'CONFIRMATION_LOCKED')) throw e
  }
  return commit()
}
export interface ItemForm {
  metric_name: string; result_text: string; unit_original: string
  reference_text: string; standard_metric_id: string | null
}

export function groupedItems(items: ConfirmationItem[]) {
  return {
    pending: items.filter(i => i.review_status === 'PENDING' && i.resolution !== 'REMOVED'),
    adopted: items.filter(i => i.review_status === 'RESOLVED' && i.resolution !== 'REMOVED'),
    removed: items.filter(i => i.resolution === 'REMOVED'),
  }
}

export function itemForm(item: ConfirmationItem | null): ItemForm {
  return { metric_name: item?.metric_name || '', result_text: item?.result_text || '',
    unit_original: item?.unit_original || '', reference_text: item?.reference_text || '',
    standard_metric_id: item?.standard_metric_id || null }
}

export function itemPayload(form: ItemForm, item: ConfirmationItem | null, keepOriginal = false): Record<string, unknown> {
  const values = { metric_name: form.metric_name.trim(), result_text: form.result_text.trim(),
    unit_original: form.unit_original.trim() || null, reference_text: form.reference_text.trim() || null,
    standard_metric_id: keepOriginal ? null : form.standard_metric_id }
  if (!item) return values
  const changes: Record<string, unknown> = {}
  for (const key of Object.keys(values) as (keyof typeof values)[]) {
    if (values[key] !== item[key]) changes[key] = values[key]
  }
  const keys = Object.keys(changes)
  const resolution = keepOriginal ? 'KEEP_ORIGINAL_NAME'
    : keys.length === 1 && keys[0] === 'standard_metric_id' && values.standard_metric_id
      ? 'STANDARD_METRIC_SELECTED' : keys.length ? 'CORRECTED' : 'ACCEPTED'
  return { ...changes, resolution }
}

export const confirmationErrorMessages: Record<string, string> = {
  REVIEW_PENDING: '还有待确认项目，请先完成核对。',
  INVALID_REPORT_DATE: '请填写有效的检验日期和时间。',
  NO_REPORT_ITEMS: '请至少保留一项检验结果。',
  INVALID_CONFIRMATION_ITEM: '请填写指标名称和结果，并检查处理方式。',
  STANDARD_METRIC_NOT_FOUND: '请选择有效的标准指标，或明确选择按原名称保存。',
  CONFIRMATION_SOURCE_INVALID: '确认来源不完整，请重试；无需重新识别。',
  CONFIRMATION_NOT_READY: '该任务尚不能确认，请返回查看任务状态。',
  CONFIRMATION_LOCKED: '报告已经保存，确认内容已锁定。',
  REPORT_ASSET_REQUIRED: '请先上传至少一张原始报告图片。',
  PROFILE_NOT_FOUND: '所选健康档案不可用，请重新选择。',
}
