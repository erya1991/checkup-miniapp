<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { reportsPath, reportDestination, mergeReportPage, type ReportCard, type ReportPage } from '../../reports'
const profile = ref<Profile | null>(null)
const items = ref<ReportCard[]>([])
const loading = ref(false)
const error = ref('')
const more = ref(false)
let page = 0
let version = 0
onShow(() => load(false))
async function load(append = false) {
  if (append && (loading.value || !more.value)) return
  const run = ++version
  loading.value = true; error.value = ''
  if (!append) { items.value = []; profile.value = null; page = 0; more.value = false }
  try {
    const me = await ensureLogin()
    if (!me.default_health_profile_id) return
    const selected = await request<Profile>(`/health-profiles/${me.default_health_profile_id}`)
    const next = await request<ReportPage>(reportsPath(selected.id, append ? page + 1 : 1))
    if (run !== version) return
    profile.value = selected; page = next.page; more.value = next.has_more
    items.value = mergeReportPage(items.value, next.items, append)
  } catch (e) { if (run === version) error.value = e instanceof Error ? e.message : '加载失败' }
  finally { if (run === version) loading.value = false }
}
function go(url: string) { uni.navigateTo({ url }) }
</script>
<template>
  <view class="page">
    <text class="title">检验报告</text>
    <button @click="go('/pages/profile-metrics/index')">我的指标</button>
    <text v-if="profile">当前档案：{{ profile.display_name }}</text>
    <button @click="go('/pages/profiles/index')">切换健康档案</button>
    <text v-if="loading">正在加载...</text>
    <view v-if="error"><text>{{ error }}</text><button @click="load(page > 0)">重试</button></view>
    <view v-if="!loading && !error && !items.length">
      <text>{{ profile ? '暂无正式检验报告' : '请先选择健康档案' }}</text>
      <button @click="go(profile ? '/pages/upload/index?new=1' : '/pages/profiles/index')">{{ profile ? '上传报告' : '选择档案' }}</button>
    </view>
    <view v-for="item in items" :key="item.id" class="card" @click="go(reportDestination(item.id))">
      <text>{{ item.examination_date }} {{ item.examination_time || '' }}</text>
      <text v-if="item.hospital_name">{{ item.hospital_name }}</text>
      <text v-if="item.report_category">{{ item.report_category }}</text>
      <text>{{ item.item_count }} 项检验结果 · {{ item.abnormal_count }} 项有异常标记</text>
      <text v-if="item.report_no">报告编号：{{ item.report_no }}</text>
    </view>
    <button v-if="more" :disabled="loading" @click="load(true)">加载更多</button>
  </view>
</template>
<style scoped>
.page, .card { display: flex; flex-direction: column; gap: 20rpx; padding: 32rpx; }
.card { border: 1px solid #ddd; border-radius: 12rpx; }
.title { font-size: 38rpx; font-weight: 600; }
</style>
