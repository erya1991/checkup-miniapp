<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { request, type Profile } from '../../api'
import { displayUnit, abnormalLabel, migrateWithConfirmation, deletedReportDestination, type ReportDetail } from '../../reports'
const id = ref('')
const report = ref<ReportDetail | null>(null)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const migrationTargets = ref<Profile[]>([])
onLoad(q => { id.value = q?.id || '' })
onShow(load)
async function load() {
  if (!id.value) return
  loading.value = true; error.value = ''; report.value = null
  try { report.value = await request<ReportDetail>(`/reports/${id.value}`) }
  catch (e) { error.value = e instanceof Error ? e.message : '加载失败' }
  finally { loading.value = false }
}
async function migrate() {
  if (busy.value || !report.value) return
  busy.value = true; error.value = ''
  try {
    migrationTargets.value = (await request<Profile[]>('/health-profiles')).filter(p => p.id !== report.value?.health_profile_id)
    if (!migrationTargets.value.length) uni.showToast({ title: '没有其它可迁移档案', icon: 'none' })
  } catch (e) { error.value = e instanceof Error ? e.message : '档案加载失败' }
  finally { busy.value = false }
}
async function selectTarget(target: Profile) {
  if (busy.value || !report.value) return
  busy.value = true; error.value = ''
  try {
    const confirm = await uni.showModal({ title: '迁移报告', content: `将整份报告从「${report.value.health_profile.display_name}」迁移到「${target.display_name}」？` })
    if (!confirm.confirm) return
    await performMigration(target.id)
    migrationTargets.value = []
  } catch (e) { error.value = e instanceof Error ? e.message : '迁移失败' }
  finally { busy.value = false }
}
async function performMigration(target: string) {
  const moved = await migrateWithConfirmation(
    body => request<ReportDetail>(`/reports/${id.value}/migrate`, 'POST', body), target,
    async prompt => {
      const confirm = await uni.showModal({ title: '目标档案存在疑似重复报告',
        content: prompt.candidates.map(c => `${c.examination_date} ${c.hospital_name || ''} ${c.report_no || ''}`).join('\n'),
        confirmText: '仍然迁移', cancelText: '取消' })
      return !!confirm.confirm
    },
  )
  if (moved) { report.value = moved; uni.showToast({ title: '迁移成功', icon: 'success' }) }
}
async function remove() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    const confirm = await uni.showModal({ title: '删除报告', content: '删除后将同时删除该报告的检验结果、原始图片及识别数据，无法恢复。', confirmText: '删除', confirmColor: '#b42318' })
    if (!confirm.confirm) return
    await request(`/reports/${id.value}`, 'DELETE')
    report.value = null
    uni.redirectTo({ url: deletedReportDestination })
  } catch (e) { error.value = e instanceof Error ? e.message : '删除失败' }
  finally { busy.value = false }
}
function assets() { uni.navigateTo({ url: `/pages/report-assets/index?id=${encodeURIComponent(id.value)}` }) }
</script>
<template>
  <view class="page">
    <text v-if="loading">正在加载...</text>
    <view v-if="error"><text>{{ error }}</text><button :disabled="busy" @click="load">重新加载</button></view>
    <view v-if="report" class="content">
      <view class="card">
        <text>所属档案：{{ report.health_profile.display_name }}</text>
        <text>医院：{{ report.hospital_name || '未填写' }}</text>
        <text>检验日期：{{ report.examination_date }} {{ report.examination_time || '' }}</text>
        <text>报告分类：{{ report.report_category || '未填写' }}</text>
        <text>报告编号：{{ report.report_no || '未填写' }}</text>
        <text>{{ report.item_count }} 项检验结果</text>
      </view>
      <button @click="assets">查看原始报告</button>
      <view v-for="item in report.results" :key="item.id" class="card">
        <text>{{ item.metric_name }}</text>
        <text>{{ item.result_text }} {{ displayUnit(item) }} {{ abnormalLabel(item.abnormal) }}</text>
        <text v-if="item.reference_text">参考范围：{{ item.reference_text }}</text>
        <text>{{ item.standard_metric ? `标准指标：${item.standard_metric.name}（${item.standard_metric.code}）` : '未关联标准指标' }}</text>
      </view>
      <view v-if="migrationTargets.length" class="card">
        <text>选择目标健康档案</text>
        <button v-for="target in migrationTargets" :key="target.id" :disabled="busy" @click="selectTarget(target)">{{ target.display_name }}</button>
        <button :disabled="busy" @click="migrationTargets = []">取消</button>
      </view>
      <button :disabled="busy" @click="migrate">迁移到其他档案</button>
      <button :disabled="busy" class="danger" @click="remove">删除报告</button>
    </view>
  </view>
</template>
<style scoped>
.page, .content, .card { display: flex; flex-direction: column; gap: 20rpx; }
.page { padding: 32rpx; } .card { padding: 24rpx; border: 1px solid #ddd; border-radius: 12rpx; }
.danger { color: #b42318; }
</style>
