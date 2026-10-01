<script setup lang="ts">
import { ref } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { abnormalLabel } from '../../reports'
import { metricsPath, metricDestination, appFontSize, mergePage, examinationLabel, requestGuard, type MetricCard, type PageResult } from '../../profile-metrics'
const profile = ref<Profile | null>(null), items = ref<MetricCard[]>([])
const loading = ref(false), error = ref(''), more = ref(false)
const guard = requestGuard()
let page = 0
const fontSize = ref(16)
onShow(() => {
  fontSize.value = appFontSize(uni.getAppBaseInfo())
  load()
})
onHide(() => guard.invalidate())
onUnload(() => guard.invalidate())
async function load(append = false) {
  if (append && (loading.value || !more.value)) return
  const run = guard.next(), previousProfile = profile.value?.id
  loading.value = true; error.value = ''
  if (!append) { items.value = []; profile.value = null; page = 0; more.value = false }
  try {
    const me = await ensureLogin()
    if (!guard.current(run)) return
    if (!me.default_health_profile_id) {
      items.value = []; profile.value = null; more.value = false; page = 0
      return
    }
    const selected = await request<Profile>(`/health-profiles/${encodeURIComponent(me.default_health_profile_id)}`)
    if (!guard.current(run)) return
    if (append && previousProfile !== selected.id) { await load(false); return }
    profile.value = selected
    const next = await request<PageResult<MetricCard>>(metricsPath(selected.id, append ? page + 1 : 1))
    if (!guard.current(run)) return
    items.value = mergePage(items.value, next.items, append); page = next.page; more.value = next.has_more
  } catch { if (guard.current(run)) error.value = '指标加载失败，请检查网络后重试。' }
  finally { if (guard.current(run)) loading.value = false }
}
function go(url: string) { uni.navigateTo({ url }) }
function reports() { uni.redirectTo({ url: '/pages/reports/index' }) }
</script>
<template>
  <view class="page" :style="{ fontSize: fontSize + 'px' }">
    <view class="views"><button @click="reports">检验报告</button><text class="title">我的指标</text></view>
    <text v-if="profile">当前档案：{{ profile.display_name }}</text>
    <button @click="go('/pages/profiles/index')">切换健康档案</button>
    <text v-if="loading">正在加载...</text>
    <view v-if="error"><text>{{ error }}</text><button @click="load(page > 0)">重试</button></view>
    <view v-if="!loading && !error && !items.length">
      <text>{{ profile ? '暂无可聚合的标准指标' : '请先选择健康档案' }}</text>
      <button @click="go(profile ? '/pages/reports/index' : '/pages/profiles/index')">{{ profile ? '查看检验报告' : '选择档案' }}</button>
    </view>
    <view v-for="item in items" :key="item.standard_metric.id" class="card" @click="go(metricDestination(item.standard_metric.id))">
      <text class="title">{{ item.standard_metric.name }}（{{ item.standard_metric.code }}）</text>
      <text>{{ item.is_favorite ? '已关注' : '未关注' }} · {{ item.history_count }} 条历史</text>
      <text class="value">{{ item.latest.result_text }} {{ item.latest.unit || '' }} {{ abnormalLabel(item.latest.abnormal) }}</text>
      <text>{{ examinationLabel(item.latest) }}</text>
    </view>
    <button v-if="more" :disabled="loading" @click="load(true)">加载更多</button>
  </view>
</template>
<style scoped>
.page, .card { display: flex; flex-direction: column; gap: 12px; padding: 16px; }
.card { background: white; border: 1px solid #ddd; border-radius: 6px; min-height: 44px; }
.views { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.title { font-size: 1.125em; font-weight: 600; overflow-wrap: anywhere; }
.value { font-size: 1.25em; }
button { font-size: inherit; margin: 0; }
</style>
