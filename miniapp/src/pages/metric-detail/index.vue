<script setup lang="ts">
import { ref, computed } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { abnormalLabel, reportDestination } from '../../reports'
import MetricTrendChart from '../../components/MetricTrendChart.vue'
import { metricPath, favoritePath, appFontSize, mergePage, defaultSeries, selectedSeries, examinationLabel, emptyTrendMessage, requestGuard, changeFavorite,
  type MetricCard, type MetricHistoryItem, type MetricTrend, type TrendPoint, type PageResult } from '../../profile-metrics'
const profile = ref<Profile | null>(null), info = ref<MetricCard | null>(null)
const trend = ref<MetricTrend | null>(null), history = ref<MetricHistoryItem[]>([])
const loading = ref(false), historyLoading = ref(false), favoriteLoading = ref(false)
const error = ref(''), historyError = ref(''), favoriteError = ref(''), more = ref(false)
const seriesKey = ref(''), selectedPoint = ref<TrendPoint | null>(null), fontSize = ref(16)
const series = computed(() => selectedSeries(trend.value?.series || [], seriesKey.value))
const guard = requestGuard()
let id = '', page = 0, activeRun = 0
onLoad(query => { id = query?.id || '' })
onShow(() => { fontSize.value = appFontSize(uni.getAppBaseInfo()); load() })
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
      ? '当前档案暂无该指标的正式历史，可返回我的指标。' : '指标详情加载失败，请重试。'
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
  } catch { if (guard.current(run)) historyError.value = '历史加载失败，请重试。' }
  finally { if (guard.current(run)) historyLoading.value = false }
}
async function toggleFavorite() {
  if (!profile.value || !info.value || favoriteLoading.value) return
  const run = activeRun, path = favoritePath(profile.value.id, id), current = info.value.is_favorite
  favoriteLoading.value = true; favoriteError.value = ''
  try {
    const state = await changeFavorite(method => request<{ is_favorite: boolean }>(path, method), current)
    if (guard.current(run) && info.value) info.value.is_favorite = state
  } catch { if (guard.current(run)) favoriteError.value = '关注操作失败，请重试。' }
  finally { if (guard.current(run)) favoriteLoading.value = false }
}
function selectUnit(key: string) {
  seriesKey.value = key; selectedPoint.value = series.value?.points.at(-1) || null
}
function report(reportId: string) { uni.navigateTo({ url: reportDestination(reportId) }) }
function backToMetrics() { uni.redirectTo({ url: '/pages/profile-metrics/index' }) }
function profiles() { uni.navigateTo({ url: '/pages/profiles/index' }) }
</script>
<template>
  <view class="page" :style="{ fontSize: fontSize + 'px' }">
    <button @click="backToMetrics">返回我的指标</button>
    <text v-if="profile">当前档案：{{ profile.display_name }}</text>
    <button @click="profiles">切换健康档案</button>
    <text v-if="loading">正在加载...</text>
    <view v-if="error"><text>{{ error }}</text><button @click="load">重试</button></view>
    <template v-if="info && !loading && !error">
      <text class="title">{{ info.standard_metric.name }}（{{ info.standard_metric.code }}）</text>
      <button :disabled="favoriteLoading" :loading="favoriteLoading" @click="toggleFavorite">{{ info.is_favorite ? '取消关注' : '关注指标' }}</button>
      <text v-if="favoriteError">{{ favoriteError }}</text>
      <view class="card">
        <text class="heading">最新正式结果</text>
        <text class="value">{{ info.latest.result_text }} {{ info.latest.unit || '' }} {{ abnormalLabel(info.latest.abnormal) }}</text>
        <text>{{ examinationLabel(info.latest) }}</text>
        <text>参考范围：{{ info.latest.reference_text || '未记录' }}</text>
        <text v-if="!info.latest.abnormal">未记录异常标记</text>
      </view>
      <view class="card">
        <text class="heading">数值趋势</text>
        <text v-if="!trend?.plottable_count">{{ emptyTrendMessage }}</text>
        <template v-else>
          <view v-if="trend && trend.series.length > 1" class="units">
            <button v-for="unit in trend.series" :key="unit.series_key" :class="{ active: seriesKey === unit.series_key }" @click="selectUnit(unit.series_key)">{{ unit.unit || '无单位' }}</button>
          </view>
          <text>当前单位：{{ series?.unit || '无单位' }} · {{ series?.points.length || 0 }} 个数值点</text>
          <MetricTrendChart v-if="series" :points="series.points" :selected-id="selectedPoint?.lab_result_id || ''" @select="selectedPoint = $event" />
          <view v-if="selectedPoint" class="point-summary">
            <text>{{ examinationLabel(selectedPoint) }}</text>
            <text>{{ selectedPoint.result_text }} {{ selectedPoint.unit || '' }} {{ abnormalLabel(selectedPoint.abnormal) }}</text>
            <text>参考范围：{{ selectedPoint.reference_text || '未记录' }}</text>
            <text v-if="!selectedPoint.abnormal">未记录异常标记</text>
            <button @click="report(selectedPoint.report_id)">查看对应报告</button>
          </view>
        </template>
      </view>
      <text class="heading">完整历史（{{ info.history_count }} 条）</text>
      <view v-for="row in history" :key="row.lab_result_id" class="card" @click="report(row.report_id)">
        <text>{{ examinationLabel(row) }}</text>
        <text class="value">{{ row.result_text }} {{ row.unit || '' }} {{ abnormalLabel(row.abnormal) }}</text>
        <text>参考范围：{{ row.reference_text || '未记录' }}</text>
        <text v-if="!row.abnormal">未记录异常标记</text>
        <text v-if="row.hospital_name">{{ row.hospital_name }}</text>
        <text>查看对应报告与原始报告</text>
      </view>
      <text v-if="historyError">{{ historyError }}</text>
      <button v-if="more" :disabled="historyLoading" :loading="historyLoading" @click="loadMore">{{ historyError ? '重试加载历史' : '加载更多历史' }}</button>
    </template>
  </view>
</template>
<style scoped>
.page, .card, .point-summary { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
.card { background: white; border: 1px solid #ddd; border-radius: 6px; }
.title { font-size: 1.25em; font-weight: 600; }
.heading { font-size: 1.125em; font-weight: 600; }
.value { font-size: 1.25em; }
.units { display: flex; gap: 8px; flex-wrap: wrap; }
.active { background: #087d44; color: white; }
button { font-size: inherit; margin: 0; }
text { overflow-wrap: anywhere; }
</style>
