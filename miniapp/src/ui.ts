export function fontScale(info: { fontSizeScaleFactor?: number; fontSizeSetting?: number; hostFontSizeSetting?: number | string }) {
  const setting = Number(info.fontSizeSetting || info.hostFontSizeSetting || 16)
  const scale = Number(info.fontSizeScaleFactor) || setting / 16
  return Number.isFinite(scale) ? Math.max(1, Math.min(2, scale)) : 1
}

// Never surface raw transport exceptions, server messages or private resource keys.
export function userError(error: unknown, fallback = '暂时无法加载，请检查网络后重试。'): string {
  const failure = error as { status?: number; code?: string }
  if (failure?.status === 401) return '登录已失效，请重试以重新登录。'
  const messages: Record<string, string> = {
    PROFILE_NOT_FOUND: '该健康档案已不存在，请重新选择档案。',
    INGESTION_NOT_FOUND: '这份待处理报告已不存在，请返回查看其它报告。',
    REPORT_NOT_FOUND: '这份报告已不存在，请返回报告列表。',
    INGESTION_INPUT_FROZEN: '识别已开始，图片与页序不能再修改。',
    INGESTION_NOT_READY: '请先完成图片上传，再开始识别。',
    PROFILE_DELETE_BUSY: '该档案有报告正在识别，请等待识别结束后再删除。',
  }
  return messages[failure?.code || ''] || fallback
}
