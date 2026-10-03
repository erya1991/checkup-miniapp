<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { abnormalDescription, reportDestination } from '../../reports'
import MetricTrendChart from '../../components/MetricTrendChart.vue'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import StatusTag from '../../components/StatusTag.vue'
import { openReports } from '../../navigation'
import { userError } from '../../ui'
import { metricPath, favoritePath, mergePage, defaultSeries, selectedSeries, examinationLabel, emptyTrendMessage, requestGuard, changeFavorite,
  type MetricCard, type MetricHistoryItem, type MetricTrend, type TrendPoint, type PageResult } from '../../profile-metrics'
const profile = ref<Profile | null>(null), info = ref<MetricCard | null>(null)
const trend = ref<MetricTrend | null>(null), history = ref<MetricHistoryItem[]>([])
const loading = ref(false), historyLoading = ref(false), favoriteLoading = ref(false)
const error = ref(''), historyError = ref(''), favoriteError = ref(''), more = ref(false)
const seriesKey = ref(''), selectedPoint = ref<TrendPoint | null>(null)
const series = computed(() => selectedSeries(trend.value?.series || [], seriesKey.value))
const guard = requestGuard()
let id = '', page = 0, activeRun = 0
onLoad(query => { id = query?.id || '' })
onShow(load)
onHide(() => guard.invalidate())
onUnload(() => guard.invalidate())
async function load() {
  const run = guard.next(); activeRun = run
  loading.value = true; error.value = ''; historyError.value = ''; favoriteError.value = ''
  profile.value = null; info.value = null; trend.value = null; history.value = []
  page = 0; more.value = false; seriesKey.value = ''; selectedPoint.value = null
  historyLoading.value = false; favoriteLoading.value = false
  try {
    const me = await ensureLogin()
    if (!guard.current(run)) return
    if (!me.default_health_profile_id) { error.value = '请先选择健康档案。'; return }
    const p = await request<Profile>(`/health-profiles/${encodeURIComponent(me.default_health_profile_id)}`)
    if (!guard.current(run)) return
    profile.value = p
    const [detail, chart, rows] = await Promise.all([
      request<MetricCard>(metricPath(p.id, id)),
      request<MetricTrend>(metricPath(p.id, id, 'trend')),
      request<PageResult<MetricHistoryItem>>(metricPath(p.id, id, 'history')),
    ])
    if (!guard.current(run)) return
    info.value = detail; trend.value = chart; history.value = rows.items
    page = rows.page; more.value = rows.has_more; seriesKey.value = defaultSeries(chart.series)
    selectedPoint.value = series.value?.points.at(-1) || null
  } catch (e) {
    if (guard.current(run)) error.value = (e as { code?: string }).code === 'PROFILE_METRIC_NOT_FOUND'
      ? '当前档案暂无该指标的正式历史，可返回我的指标。' : userError(e, '指标详情加载失败，请重试。')
  } finally { if (guard.current(run)) loading.value = false }
}
async function loadMore() {
  if (loading.value || historyLoading.value || !more.value || !profile.value) return
  const run = activeRun, profileId = profile.value.id
  historyLoading.value = true; historyError.value = ''
  try {
    const next = await request<PageResult<MetricHistoryItem>>(metricPath(profileId, id, 'history', page + 1))
    if (!guard.current(run)) return
    history.value = mergePage(history.value, next.items, true); page = next.page; more.value = next.has_more
  } catch (e) { if (guard.current(run)) historyError.value = userError(e, '历史加载失败，请重试。') }
  finally { if (guard.current(run)) historyLoading.value = false }
}
async function toggleFavorite() {
  if (!profile.value || !info.value || favoriteLoading.value) return
  const run = activeRun, path = favoritePath(profile.value.id, id), current = info.value.is_favorite
  favoriteLoading.value = true; favoriteError.value = ''
  try {
    const state = await changeFavorite(method => request<{ is_favorite: boolean }>(path, method), current)
    if (guard.current(run) && info.value) info.value.is_favorite = state
  } catch (e) { if (guard.current(run)) favoriteError.value = userError(e, '关注操作失败，请重试。') }
  finally { if (guard.current(run)) favoriteLoading.value = false }
}
function selectUnit(key: string) {
  seriesKey.value = key; selectedPoint.value = series.value?.points.at(-1) || null
}
function report(reportId: string) { uni.navigateTo({ url: reportDestination(reportId) }) }
function backToMetrics() { openReports('metrics') }
</script>
<template>
  <PageContainer>
    <UiState v-if="loading" type="loading" title="正在加载指标详情" />
    <UiState v-if="error" type="error" title="暂时无法查看指标" :description="error" action="重试" @action="load" />
    <button v-if="error" class="text-action" @click="backToMetrics">查看我的指标</button>
    <template v-if="info && !loading && !error">
      <view class="section-heading">
        <view class="metric-heading">
          <text class="muted">{{ profile?.display_name }}的指标</text>
          <text class="title">{{ info.standard_metric.name }}</text>
        </view>
        <button class="secondary" :disabled="favoriteLoading" :loading="favoriteLoading" @click="toggleFavorite">{{ info.is_favorite ? '取消关注' : '关注指标' }}</button>
      </view>
      <text v-if="favoriteError" class="error">{{ favoriteError }}</text>
      <view class="card">
        <text class="section-title">最新正式结果</text>
        <view class="result-line">
          <text class="value">{{ info.latest.result_text }} <text class="unit">{{ info.latest.unit || '' }}</text></text>
          <StatusTag v-if="abnormalDescription(info.latest.abnormal)" tone="abnormal" :label="abnormalDescription(info.latest.abnormal)" />
        </view>
        <text class="muted">{{ examinationLabel(info.latest) }}</text>
        <text>参考范围：{{ info.latest.reference_text || '未记录' }}</text>
      </view>
      <view class="card">
        <text class="section-title">数值趋势</text>
        <UiState v-if="!trend?.plottable_count" type="empty" title="暂无数值趋势" :description="emptyTrendMessage" />
        <template v-else>
          <view v-if="trend && trend.series.length > 1" class="units">
            <text class="muted">选择单位查看，同一单位单独成图</text>
            <view class="actions">
              <button v-for="unit in trend.series" :key="unit.series_key" :class="seriesKey === unit.series_key ? 'selected-unit' : 'secondary'" @click="selectUnit(unit.series_key)">{{ unit.unit || '无单位' }}</button>
            </view>
          </view>
          <text class="muted">{{ series?.unit || '无单位' }} · {{ series?.points.length || 0 }} 次检验</text>
          <MetricTrendChart v-if="series" :points="series.points" :selected-id="selectedPoint?.lab_result_id || ''" @select="selectedPoint = $event" />
          <view v-if="selectedPoint" class="point-summary">
            <text class="muted">选中的检验结果 · {{ examinationLabel(selectedPoint) }}</text>
            <view class="result-line">
              <text class="value">{{ selectedPoint.result_text }} <text class="unit">{{ selectedPoint.unit || '' }}</text></text>
              <StatusTag v-if="abnormalDescription(selectedPoint.abnormal)" tone="abnormal" :label="abnormalDescription(selectedPoint.abnormal)" />
            </view>
            <text>本次参考范围：{{ selectedPoint.reference_text || '未记录' }}</text>
            <button class="primary" @click="report(selectedPoint.report_id)">查看来源报告</button>
          </view>
        </template>
      </view>
      <text class="section-title">完整历史（{{ info.history_count }} 条）</text>
      <text class="muted">同一天的多次检验、不同单位及文本结果分别保留。</text>
      <view v-for="row in history" :key="row.lab_result_id" class="card" @click="report(row.report_id)">
        <text class="muted">{{ examinationLabel(row) }}</text>
        <view class="result-line">
          <text class="value">{{ row.result_text }} <text class="unit">{{ row.unit || '' }}</text></text>
          <StatusTag v-if="abnormalDescription(row.abnormal)" tone="abnormal" :label="abnormalDescription(row.abnormal)" />
        </view>
        <text>参考范围：{{ row.reference_text || '未记录' }}</text>
        <text v-if="row.hospital_name" class="muted">{{ row.hospital_name }}</text>
        <text class="report-link">查看来源报告与原图 ›</text>
      </view>
      <UiState v-if="historyError" type="error" title="历史暂时无法加载" :description="historyError" action="重试加载历史" @action="loadMore" />
      <button v-if="more && !historyError" class="secondary" :disabled="historyLoading" :loading="historyLoading" @click="loadMore">加载更多历史</button>
    </template>
  </PageContainer>
</template>
<style scoped>
.metric-heading, .units, .point-summary { display: flex; flex-direction: column; gap: 16rpx; }
.result-line { display: flex; flex-wrap: wrap; gap: 16rpx; align-items: center; }
.value { font-size: var(--font-section); font-weight: 600; }
.unit { font-size: var(--font-note); font-weight: 400; }
.selected-unit { color: var(--primary-text); background: #e9f7ed; border: 2rpx solid var(--primary-text); }
.point-summary { border-top: 1rpx solid var(--border); padding-top: 24rpx; }
.report-link { color: var(--primary-text); font-size: var(--font-note); }
</style>
