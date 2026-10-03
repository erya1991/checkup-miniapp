<script setup lang="ts">
import { ref } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, type Ingestion, type Profile } from '../../api'
import { reportsPath, reportDestination, abnormalLabel, type ReportCard, type ReportPage } from '../../reports'
import { metricsPath, metricDestination, requestGuard, type MetricCard, type PageResult } from '../../profile-metrics'
import { pendingSummary, recentReports, favoriteSummary } from '../../productization'
import { ingestionTasksPath, taskDestination, taskStatusLabels } from '../../ingestion-tasks'
import { navigate, newUploadPath, openReports } from '../../navigation'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import ProfileContext from '../../components/ProfileContext.vue'
import StatusTag from '../../components/StatusTag.vue'
const loading = ref(true), error = ref('')
const current = ref<Profile | null>(null)
const pending = ref<{ count: number; first: Ingestion | null }>({ count: 0, first: null })
const reports = ref<ReportCard[]>([]), favorites = ref<MetricCard[]>([])
const guard = requestGuard()
onShow(load); onHide(() => guard.invalidate())
async function load() {
  const run = guard.next()
  loading.value = true; error.value = ''; current.value = null
  pending.value = { count: 0, first: null }; reports.value = []; favorites.value = []
  try {
    const me = await ensureLogin()
    if (!me.default_health_profile_id || !guard.current(run)) return
    const profileId = me.default_health_profile_id
    const [profile, ingestions, formal, metrics] = await Promise.all([
      request<Profile>(`/health-profiles/${profileId}`), request<Ingestion[]>(ingestionTasksPath(profileId)),
      request<ReportPage>(reportsPath(profileId)), request<PageResult<MetricCard>>(metricsPath(profileId)),
    ])
    if (!guard.current(run)) return
    current.value = profile; pending.value = pendingSummary(ingestions)
    reports.value = recentReports(formal.items); favorites.value = favoriteSummary(metrics.items)
  } catch (e) { if (guard.current(run)) error.value = userError(e) }
  finally { if (guard.current(run)) loading.value = false }
}
function continueReport() { const url = pending.value.first && taskDestination(pending.value.first); if (url) navigate(url) }
</script>
<template>
  <PageContainer>
    <UiState v-if="loading" type="loading" title="正在加载报告" />
    <UiState v-else-if="error" type="error" title="暂时无法加载" :description="error" action="重试" @action="load" />
    <UiState v-else-if="!current" type="empty" title="为自己创建健康档案" description="按家庭成员分别整理报告，查看各自的检验历史。" action="创建本人档案" @action="navigate('/pages/profile-edit/index')" />
    <template v-else>
      <ProfileContext :name="current.display_name" @choose="navigate('/pages/profiles/index')" />
      <view class="card">
        <text class="title">把检验报告整理好</text>
        <text class="muted">拍照或从相册选择报告，识别后由你核对并保存。</text>
        <button class="primary" @click="navigate(newUploadPath())">上传检验报告</button>
      </view>
      <view v-if="pending.first" class="card">
        <view class="section-heading"><text class="section-title">待处理报告 · {{ pending.count }} 份</text><StatusTag :label="taskStatusLabels[pending.first.status]" tone="warning" /></view>
        <text class="muted">{{ pending.first.assets.length }} 页原图 · 完成核对并保存后才会进入正式报告</text>
        <button class="secondary" @click="continueReport">继续处理</button>
        <button class="text-action" @click="navigate('/pages/ingestion-tasks/index')">查看全部待处理报告</button>
      </view>
      <template v-if="reports.length">
        <view class="section-heading"><text class="section-title">最近报告</text><button class="text-action" @click="openReports()">查看全部</button></view>
        <view v-for="report in reports" :key="report.id" class="card" @click="navigate(reportDestination(report.id))">
          <text class="section-title">{{ report.examination_date }} {{ report.examination_time || '' }}</text>
          <text v-if="report.hospital_name || report.report_category">{{ [report.hospital_name, report.report_category].filter(Boolean).join(' · ') }}</text>
          <text class="muted">{{ report.item_count }} 项检验结果<text v-if="report.abnormal_count"> · {{ report.abnormal_count }} 项有异常标记</text></text>
        </view>
      </template>
      <template v-if="favorites.length">
        <view class="section-heading"><text class="section-title">关注指标</text><button class="text-action" @click="openReports('metrics')">我的指标</button></view>
        <view v-for="metric in favorites" :key="metric.standard_metric.id" class="card" @click="navigate(metricDestination(metric.standard_metric.id))">
          <text class="section-title">{{ metric.standard_metric.name }}</text>
          <view class="actions"><text>{{ metric.latest.result_text }} {{ metric.latest.unit || '' }}</text><StatusTag v-if="abnormalLabel(metric.latest.abnormal)" :label="abnormalLabel(metric.latest.abnormal)" tone="abnormal" /></view>
          <text class="muted">{{ metric.latest.examination_date }} {{ metric.latest.examination_time || '' }}</text>
        </view>
      </template>
    </template>
  </PageContainer>
</template>
