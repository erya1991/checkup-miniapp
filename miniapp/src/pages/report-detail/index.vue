<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { displayUnit, abnormalDescription, resultIdentityHint, migrateWithConfirmation, type ReportDetail } from '../../reports'
import { requestGuard } from '../../profile-metrics'
import { openReports } from '../../navigation'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import StatusTag from '../../components/StatusTag.vue'
const id = ref(''), report = ref<ReportDetail | null>(null)
const loading = ref(false), busy = ref(false), choosingMore = ref(false), error = ref('')
const migrationTargets = ref<Profile[]>([])
const guard = requestGuard()
onLoad(q => { id.value = q?.id || '' })
onShow(load)
onHide(() => guard.invalidate())
onUnload(() => guard.invalidate())
async function load() {
  const run = guard.next()
  loading.value = true; error.value = ''; report.value = null; migrationTargets.value = []; busy.value = false
  try {
    if (!id.value) { error.value = '没有找到这份报告，请返回报告列表。'; return }
    await ensureLogin()
    if (!guard.current(run)) return
    const detail = await request<ReportDetail>(`/reports/${encodeURIComponent(id.value)}`)
    if (guard.current(run)) report.value = detail
  } catch (e) { if (guard.current(run)) error.value = userError(e, '报告暂时无法加载，请重试。') }
  finally { if (guard.current(run)) loading.value = false }
}
async function moreActions() {
  if (busy.value || choosingMore.value) return
  choosingMore.value = true
  try {
    const choice = await uni.showActionSheet({ itemList: ['迁移到其他档案', '删除报告'] })
    if (choice.tapIndex === 0) await migrate()
    if (choice.tapIndex === 1) await remove()
  } catch { /* Native action sheet cancellation needs no error feedback. */ }
  finally { choosingMore.value = false }
}
async function migrate() {
  if (busy.value || !report.value) return
  const run = guard.next(), currentProfile = report.value.health_profile_id
  busy.value = true; error.value = ''
  try {
    const rows = await request<Profile[]>('/health-profiles')
    if (!guard.current(run)) return
    migrationTargets.value = rows.filter(p => p.id !== currentProfile)
    if (!migrationTargets.value.length) uni.showToast({ title: '请先创建其他健康档案', icon: 'none' })
  } catch (e) { if (guard.current(run)) error.value = userError(e, '档案加载失败，请重试。') }
  finally { if (guard.current(run)) busy.value = false }
}
async function selectTarget(target: Profile) {
  if (busy.value || !report.value) return
  const run = guard.next()
  busy.value = true; error.value = ''
  try {
    const confirm = await uni.showModal({ title: '迁移报告', content: `将整份报告从「${report.value.health_profile.display_name}」迁移到「${target.display_name}」？` })
    if (!confirm.confirm || !guard.current(run)) return
    const moved = await migrateWithConfirmation(
      body => request<ReportDetail>(`/reports/${encodeURIComponent(id.value)}/migrate`, 'POST', body), target.id,
      async prompt => {
        const result = await uni.showModal({ title: '目标档案存在疑似重复报告',
          content: prompt.candidates.map(c => `${c.examination_date} ${c.hospital_name || ''} ${c.report_no || ''}`).join('\n'),
          confirmText: '仍然迁移', cancelText: '取消' })
        return !!result.confirm && guard.current(run)
      },
    )
    if (!guard.current(run)) return
    if (moved) { report.value = moved; uni.showToast({ title: '迁移成功', icon: 'success' }) }
    migrationTargets.value = []
  } catch (e) { if (guard.current(run)) error.value = userError(e, '迁移失败，请重试。') }
  finally { if (guard.current(run)) busy.value = false }
}
async function remove() {
  if (busy.value || !report.value) return
  const run = guard.next()
  busy.value = true; error.value = ''
  try {
    const confirm = await uni.showModal({ title: '永久删除报告', content: '删除后将同时删除该报告的检验结果、原始图片及识别数据，无法恢复。', confirmText: '删除', confirmColor: '#b42318' })
    if (!confirm.confirm || !guard.current(run)) return
    await request(`/reports/${encodeURIComponent(id.value)}`, 'DELETE')
    if (!guard.current(run)) return
    report.value = null
    openReports()
  } catch (e) { if (guard.current(run)) error.value = userError(e, '删除失败，请检查网络后重试。') }
  finally { if (guard.current(run)) busy.value = false }
}
function assets() { uni.navigateTo({ url: `/pages/report-assets/index?id=${encodeURIComponent(id.value)}` }) }
function reports() { openReports() }
</script>
<template>
  <PageContainer>
    <UiState v-if="loading" type="loading" title="正在加载报告" />
    <UiState v-if="error" type="error" title="暂时无法完成操作" :description="error" :action="report ? '' : '重新加载'" @action="load" />
    <button v-if="error && !report" class="text-action" @click="reports">查看其他报告</button>
    <template v-if="report && !loading">
      <view class="card">
        <text class="muted">{{ report.health_profile.display_name }}的检验报告</text>
        <text class="title">{{ report.examination_date }}</text>
        <text v-if="report.examination_time">{{ report.examination_time }}</text>
        <text v-if="report.hospital_name" class="section-title">{{ report.hospital_name }}</text>
        <text v-if="report.report_category">{{ report.report_category }}</text>
        <view class="actions">
          <text class="muted">{{ report.item_count }} 项检验结果</text>
          <StatusTag v-if="report.abnormal_count" tone="abnormal" :label="report.abnormal_count + ' 项有异常标记'" />
        </view>
        <text v-if="report.report_no" class="muted">报告编号：{{ report.report_no }}</text>
      </view>
      <button class="primary" @click="assets">查看原始报告</button>
      <text class="muted">结构化结果用于整理，原始检验报告是最终核对依据。</text>
      <text class="section-title">检验项目</text>
      <view v-for="item in report.results" :key="item.id" class="card">
        <text class="section-title">{{ item.metric_name }}</text>
        <view class="result-line">
          <text class="result-value">{{ item.result_text }} <text class="result-unit">{{ displayUnit(item) }}</text></text>
          <StatusTag v-if="abnormalDescription(item.abnormal)" tone="abnormal" :label="abnormalDescription(item.abnormal)" />
        </view>
        <text v-if="item.reference_text">参考范围：{{ item.reference_text }}</text>
        <text class="muted">{{ resultIdentityHint(item) }}</text>
      </view>
      <view v-if="migrationTargets.length" class="card">
        <text class="section-title">选择目标健康档案</text>
        <text class="muted">迁移整份报告及其检验结果，保留原始报告。</text>
        <button v-for="target in migrationTargets" :key="target.id" class="secondary" :disabled="busy" @click="selectTarget(target)">{{ target.display_name }}</button>
        <button class="text-action" :disabled="busy" @click="migrationTargets = []">取消迁移</button>
      </view>
      <button class="text-action" :disabled="busy || choosingMore" :loading="busy" @click="moreActions">更多操作</button>
    </template>
  </PageContainer>
</template>
<style scoped>
.result-line { display: flex; gap: 16rpx; align-items: center; flex-wrap: wrap; }
.result-value { font-size: var(--font-section); font-weight: 600; }
.result-unit { font-size: var(--font-note); font-weight: 400; }
</style>
