export const taskStatusLabels: Record<string, string> = {
  UPLOADING: '上传中',
  READY: '待开始识别',
  QUEUED: '排队中',
  PROCESSING: '识别中',
  OCR_FAILED: '识别失败',
  PENDING_CONFIRMATION: '识别完成，待确认',
  CONFIRMED: '已保存',
}

export function ingestionTasksPath(profileId: string): string {
  return `/ingestions?health_profile_id=${encodeURIComponent(profileId)}`
}

export function taskDestination(task: { id: string; status: string }): string | null {
  if (task.status === 'UPLOADING' || task.status === 'READY') {
    return `/pages/upload/index?id=${encodeURIComponent(task.id)}`
  }
  if (task.status === 'PENDING_CONFIRMATION') {
    return `/pages/confirmation/index?id=${encodeURIComponent(task.id)}`
  }
  if (['QUEUED', 'PROCESSING', 'OCR_FAILED'].includes(task.status)) {
    return `/pages/ocr/index?id=${encodeURIComponent(task.id)}`
  }
  return null
}
