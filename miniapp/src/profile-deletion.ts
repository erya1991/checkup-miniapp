import type { Profile } from './api'

export interface DeletionImpact {
  profile: { id: string; display_name: string }
  report_count: number
  unfinished_ingestion_count: number
  total_ingestion_count: number
  favorite_count: number
  processing_ocr_count: number
}
export interface ProfileContext { profiles: Profile[]; selected: string }
export const busyMessage = '该档案有正在识别的报告，识别结束后才能删除。'

export function deletionMessage(impact: DeletionImpact) {
  return `将永久删除「${impact.profile.display_name}」健康档案，以及全部检验报告、指标历史、关注指标、原始图片和识别数据。\n正式报告 ${impact.report_count} 份，未完成任务 ${impact.unfinished_ingestion_count} 个，关注指标 ${impact.favorite_count} 个。\n删除后无法恢复。`
}

export function profileContext(profiles: Profile[], defaultId: string | null): ProfileContext {
  return { profiles, selected: profiles.find(p => p.id === defaultId)?.id || profiles[0]?.id || '' }
}

// Dependencies keep the dangerous flow testable without simulating a WeChat device.
export async function deleteWithConfirmation(id: string, actions: {
  impact: () => Promise<DeletionImpact>
  confirm: (message: string) => Promise<boolean>
  remove: () => Promise<unknown>
  reload: () => Promise<ProfileContext>
  apply: (context: ProfileContext) => void
  notify: (message: string) => void
}) {
  const impact = await actions.impact()
  if (impact.processing_ocr_count > 0) { actions.notify(busyMessage); return 'busy' }
  if (!await actions.confirm(deletionMessage(impact))) return 'cancelled'
  let failure: unknown
  try { await actions.remove() } catch (error) {
    if ((error as { code?: string })?.code === 'PROFILE_DELETE_BUSY') {
      actions.notify(busyMessage)
      await actions.impact() // refresh the authoritative preflight; never retry DELETE automatically
      return 'busy'
    }
    failure = error
  }
  const context = await actions.reload()
  actions.apply(context)
  if (context.profiles.some(p => p.id === id)) {
    throw failure || new Error('档案仍存在，请刷新后重试。')
  }
  return 'deleted' // also handles a lost 204 or a repeated 404 after successful deletion
}
