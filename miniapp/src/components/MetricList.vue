<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { onHide } from '@dcloudio/uni-app'
import { request, type Profile } from '../api'
import { abnormalDescription } from '../reports'
import { metricsPath, metricDestination, mergePage, examinationLabel, requestGuard, type MetricCard, type PageResult } from '../profile-metrics'
import { userError } from '../ui'
import UiState from './UiState.vue'
import StatusTag from './StatusTag.vue'
const props = defineProps<{ profile: Profile | null }>()
const emit = defineEmits<{ 'show-reports': [] }>()
const items = ref<MetricCard[]>([]), loading = ref(false), error = ref(''), more = ref(false)
const guard = requestGuard()
let page = 0
watch(() => props.profile?.id, () => load(false), { immediate: true })
onHide(() => guard.invalidate())
onUnmounted(() => guard.invalidate())
async function load(append = false) {
  if (append && (loading.value || !more.value)) return
  const run = guard.next(), profileId = props.profile?.id
  loading.value = true; error.value = ''
  if (!append) { items.value = []; page = 0; more.value = false }
  if (!profileId) { loading.value = false; return }
  try {
    const next = await request<PageResult<MetricCard>>(metricsPath(profileId, append ? page + 1 : 1))
    if (!guard.current(run) || props.profile?.id !== profileId) return
    items.value = mergePage(items.value, next.items, append); page = next.page; more.value = next.has_more
  } catch (e) { if (guard.current(run)) error.value = userError(e, '指标加载失败，请检查网络后重试。') }
  finally { if (guard.current(run)) loading.value = false }
}
function detail(metricId: string) { uni.navigateTo({ url: metricDestination(metricId) }) }
</script>
<template>
  <view class="metric-list">
    <UiState v-if="loading && !items.length" type="loading" title="正在加载我的指标" />
    <UiState v-if="error" type="error" title="指标暂时无法加载" :description="error" action="重试" @action="load(page > 0)" />
    <UiState v-if="!loading && !error && !items.length" type="empty" title="还没有可查看的指标"
      description="保存并关联指标的正式报告会显示在这里；按报告原名称保存的项目仍可在报告中查看。"
      action="查看检验报告" @action="emit('show-reports')" />
    <view v-for="item in items" :key="item.standard_metric.id" class="card metric-card" @click="detail(item.standard_metric.id)">
      <view class="section-heading">
        <text class="section-title">{{ item.standard_metric.name }}</text>
        <StatusTag v-if="item.is_favorite" tone="success" label="已关注" />
      </view>
      <view class="result-line">
        <text class="value">{{ item.latest.result_text }} <text class="unit">{{ item.latest.unit || '' }}</text></text>
        <StatusTag v-if="abnormalDescription(item.latest.abnormal)" tone="abnormal" :label="abnormalDescription(item.latest.abnormal)" />
      </view>
      <text class="muted">{{ examinationLabel(item.latest) }}</text>
      <text class="muted">{{ item.history_count }} 条历史 · 查看详情与趋势 ›</text>
    </view>
    <button v-if="more && !error" class="secondary" :disabled="loading" :loading="loading" @click="load(true)">加载更多指标</button>
  </view>
</template>
<style scoped>
.metric-list { display: flex; flex-direction: column; gap: var(--page-gap); }
.metric-card { min-height: 120rpx; }
.result-line { display: flex; flex-wrap: wrap; gap: 16rpx; align-items: center; }
.value { font-size: var(--font-section); font-weight: 600; }
.unit { font-size: var(--font-note); font-weight: 400; }
</style>
