<script setup lang="ts">
import { ref } from 'vue'
import { onHide, onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { reportsPath, reportDestination, mergeReportPage, type ReportCard, type ReportPage } from '../../reports'
import { requestGuard } from '../../profile-metrics'
import { navigate, newUploadPath, type ReportView } from '../../navigation'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import ProfileContext from '../../components/ProfileContext.vue'
import MetricList from '../../components/MetricList.vue'
const view = ref<ReportView>('reports'), profile = ref<Profile | null>(null)
const items = ref<ReportCard[]>([]), loading = ref(false), error = ref(''), more = ref(false)
let page = 0
const guard = requestGuard()
onShow(() => { view.value = uni.getStorageSync('uiReportView') === 'metrics' ? 'metrics' : 'reports'; load(false) })
onHide(() => guard.invalidate())
function select(next: ReportView) { view.value = next; uni.setStorageSync('uiReportView', next) }
async function load(append = false) {
  if (append && (loading.value || !more.value)) return
  const run = guard.next()
  loading.value = true; error.value = ''
  if (!append) { items.value = []; profile.value = null; page = 0; more.value = false }
  try {
    const me = await ensureLogin()
    if (!me.default_health_profile_id || !guard.current(run)) return
    if (append && profile.value?.id !== me.default_health_profile_id) { await load(false); return }
    const selected = await request<Profile>(`/health-profiles/${me.default_health_profile_id}`)
    const next = await request<ReportPage>(reportsPath(selected.id, append ? page + 1 : 1))
    if (!guard.current(run)) return
    profile.value = selected; page = next.page; more.value = next.has_more
    items.value = mergeReportPage(items.value, next.items, append)
  } catch (e) { if (guard.current(run)) error.value = userError(e) }
  finally { if (guard.current(run)) loading.value = false }
}
</script>
<template>
  <PageContainer>
    <ProfileContext v-if="profile" :name="profile.display_name" @choose="navigate('/pages/profiles/index')" />
    <view class="view-tabs"><button :class="view === 'reports' ? 'selected' : ''" @click="select('reports')">检验报告</button><button :class="view === 'metrics' ? 'selected' : ''" @click="select('metrics')">我的指标</button></view>
    <UiState v-if="loading && !items.length" type="loading" title="正在加载报告" />
    <UiState v-else-if="error" type="error" title="暂时无法加载" :description="error" action="重试" @action="load(page > 0)" />
    <UiState v-else-if="!profile" type="empty" title="还没有健康档案" description="创建档案后，按家庭成员整理报告。" action="创建本人档案" @action="navigate('/pages/profile-edit/index')" />
    <template v-else-if="view === 'reports'">
      <UiState v-if="!items.length" type="empty" title="还没有正式检验报告" description="上传报告，核对识别结果后保存。" action="上传检验报告" @action="navigate(newUploadPath())" />
      <view v-for="item in items" :key="item.id" class="card" @click="navigate(reportDestination(item.id))">
        <text class="section-title">{{ item.examination_date }} {{ item.examination_time || '' }}</text>
        <text v-if="item.hospital_name || item.report_category">{{ [item.hospital_name, item.report_category].filter(Boolean).join(' · ') }}</text>
        <text class="muted">{{ item.item_count }} 项检验结果<text v-if="item.abnormal_count"> · {{ item.abnormal_count }} 项有异常标记</text></text>
        <text v-if="item.report_no" class="muted">报告编号：{{ item.report_no }}</text>
      </view>
      <button v-if="more" class="secondary" :loading="loading" :disabled="loading" @click="load(true)">加载更多</button>
    </template>
    <MetricList v-else :profile="profile" @show-reports="select('reports')" />
  </PageContainer>
</template>
<style scoped>
.view-tabs { display: flex; gap: 8rpx; border-bottom: 1rpx solid var(--border); }
.view-tabs button { flex: 1; background: transparent; color: var(--muted); border-radius: 0; }
.view-tabs .selected { color: var(--primary-text); border-bottom: 4rpx solid var(--primary); font-weight: 600; }
</style>
