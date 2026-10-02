<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ApiError, ensureLogin, request, type Asset, type Ingestion, type Profile } from '../../api'
import { confirmationErrorMessages, groupedItems, itemForm, itemPayload, saveThenCommit, standardMetricLabel,
  type ConfirmationItem, type ItemForm, type StandardMetric } from '../../confirmation'

interface Workspace {
  id: string; status: string; mode: string; health_profile_id: string; health_profile: Profile
  hospital_name: string | null; examination_date: string | null; examination_time: string | null
  report_no: string | null; report_category: string | null
  assets: Asset[]; items: ConfirmationItem[]; pending_count: number
}
interface CommitResult { report_id: string; status: string; item_count: number }
interface DuplicateSummary { hospital_name: string | null; examination_date: string; report_no: string | null; item_count: number }

const id = ref('')
const workspace = ref<Workspace | null>(null)
const profiles = ref<Profile[]>([])
const loading = ref(true)
const busy = ref(false)
const error = ref('')
const success = ref<CommitResult | null>(null)
const editing = ref(false)
const selected = ref<ConfirmationItem | null>(null)
const form = reactive<ItemForm>(itemForm(null))
const metricQuery = ref('')
const metrics = ref<StandardMetric[]>([])
const metricNames = ref<Record<string, string>>({})
const searching = ref(false)
const searched = ref(false)
let previewing = false
const report = reactive({ health_profile_id: '', hospital_name: '', examination_date: '',
  examination_time: '', report_no: '', report_category: '' })
const groups = computed(() => groupedItems(workspace.value?.items || []))
const profileIndex = computed(() => profiles.value.findIndex(p => p.id === report.health_profile_id))
const profileName = computed(() => profiles.value[profileIndex.value]?.display_name || workspace.value?.health_profile.display_name || '')

onLoad(params => { id.value = params?.id || '' })
onShow(() => {
  if (previewing) { previewing = false; return }
  if (!success.value) load()
})
watch(error, value => { if (value) uni.showToast({ title: value, icon: 'none', duration: 3000 }) })
function message(e: unknown) {
  return e instanceof ApiError ? confirmationErrorMessages[e.code] || e.code
    : e instanceof Error ? e.message : '操作失败，请重试'
}
function applyWorkspace(value: Workspace) {
  workspace.value = value
  report.health_profile_id = value.health_profile_id
  report.hospital_name = value.hospital_name || ''
  report.examination_date = value.examination_date || ''
  report.examination_time = value.examination_time || ''
  report.report_no = value.report_no || ''
  report.report_category = value.report_category || ''
}
async function load() {
  if (busy.value) return
  loading.value = true; error.value = ''; editing.value = false
  try {
    if (!id.value) throw new Error('任务编号缺失')
    await ensureLogin()
    const ingestion = await request<Ingestion>(`/ingestions/${id.value}`)
    if (ingestion.status === 'CONFIRMED') {
      // Read minimal success through the already-authorized idempotent endpoint.
      success.value = await request<CommitResult>(`/ingestions/${id.value}/commit`, 'POST', {})
      return
    }
    // Ingestion ownership is authoritative; the report may have been moved
    // to another owned profile before commit without changing the default.
    const value = await request<Workspace>(`/ingestions/${id.value}/confirmation`)
    profiles.value = await request<Profile[]>('/health-profiles')
    applyWorkspace(value)
  } catch (e) { workspace.value = null; error.value = message(e) }
  finally { loading.value = false }
}
function changeProfile(event: { detail: { value: string | number } }) {
  if (busy.value) return
  report.health_profile_id = profiles.value[Number(event.detail.value)]?.id || report.health_profile_id
}
async function persistReport() {
  if (!report.examination_date) throw new Error('请填写报告上的检验日期，不能使用上传日期代替。')
  const value = await request<Workspace>(`/ingestions/${id.value}/confirmation`, 'PUT', {
    ...report, hospital_name: report.hospital_name.trim() || null,
    examination_time: report.examination_time.trim() || null,
    report_no: report.report_no.trim() || null, report_category: report.report_category.trim() || null,
  })
  applyWorkspace(value)
}
async function saveReport() {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await persistReport(); uni.showToast({ title: '报告信息已保存', icon: 'success' }) }
  catch (e) { error.value = message(e) }
  finally { busy.value = false }
}
async function preview(assetId?: string) {
  const target = assetId || workspace.value?.assets[0]?.id
  if (!target) return
  try {
    const signed = await request<{ url: string }>(`/ingestions/${id.value}/assets/${target}/preview`)
    previewing = true
    await uni.previewImage({ current: signed.url, urls: [signed.url] })
  } catch (e) { previewing = false; error.value = message(e) }
}
async function edit(item: ConfirmationItem | null) {
  if (busy.value) return
  selected.value = item; Object.assign(form, itemForm(item)); editing.value = true
  metrics.value = []; metricQuery.value = ''; searched.value = false; error.value = ''
  await nextTick()
  uni.pageScrollTo({ selector: '#item-editor', duration: 200 })
}
async function searchMetrics() {
  if (searching.value || busy.value) return
  searching.value = true; error.value = ''
  try {
    metrics.value = await request<StandardMetric[]>(`/standard-metrics?q=${encodeURIComponent(metricQuery.value)}`)
    for (const metric of metrics.value) metricNames.value[metric.id] = `${metric.name}（${metric.code}）`
    searched.value = true
  } catch (e) { error.value = message(e) }
  finally { searching.value = false }
}
async function saveItem(keepOriginal = false) {
  if (busy.value) return
  if (!form.metric_name.trim() || !form.result_text.trim()) { error.value = '请填写指标名称和结果'; return }
  busy.value = true; error.value = ''
  try {
    const payload = itemPayload(form, selected.value, keepOriginal)
    const path = `/ingestions/${id.value}/confirmation/items${selected.value ? '/' + selected.value.id : ''}`
    const value = await request<Workspace>(path, selected.value ? 'PUT' : 'POST', payload)
    // Report inputs may be unsaved; item editing must not erase them.
    workspace.value = value; editing.value = false
    uni.showToast({ title: '项目已保存', icon: 'success' })
  } catch (e) { error.value = message(e) }
  finally { busy.value = false }
}
async function resolve(item: ConfirmationItem, resolution: 'ACCEPTED' | 'REMOVED') {
  if (busy.value) return
  busy.value = true; error.value = ''
  try {
    if (resolution === 'REMOVED') {
      const choice = await uni.showModal({ title: '删除错误识别', content: '此项不进入正式报告，原始识别记录仍保留。' })
      if (!choice.confirm) return
    }
    workspace.value = await request<Workspace>(`/ingestions/${id.value}/confirmation/items/${item.id}`, 'PUT', { resolution })
  } catch (e) { error.value = message(e) }
  finally { busy.value = false }
}
async function commit(acknowledgement?: string): Promise<void> {
  try {
    success.value = await request<CommitResult>(`/ingestions/${id.value}/commit`, 'POST',
      acknowledgement ? { duplicate_acknowledgement: acknowledgement } : {})
  } catch (e) {
    if (e instanceof ApiError && e.code === 'DUPLICATE_CONFIRM_REQUIRED') {
      const candidates = e.details.candidates as DuplicateSummary[]
      const summary = candidates.map(c => `${c.hospital_name || '未填写医院'} · ${c.examination_date} · ${c.report_no || '无报告号'} · ${c.item_count}项`).join('\n')
      const choice = await uni.showModal({ title: '发现疑似重复报告',
        content: `${summary}\n请核对原始报告。仍然保存将保留两份独立报告。`, confirmText: '仍然保存', cancelText: '返回修改' })
      if (choice.confirm) await commit(e.details.acknowledgement as string)
      return
    }
    if (e instanceof ApiError && e.code === 'REVIEW_PENDING') {
      uni.pageScrollTo({ selector: '#pending-items', duration: 200 })
    }
    throw e
  }
}
async function submit() {
  if (busy.value) return
  if (editing.value) { error.value = '请先保存或取消当前项目编辑'; return }
  if (groups.value.pending.length) {
    error.value = `还有 ${groups.value.pending.length} 项待确认，请先核对。`
    uni.pageScrollTo({ selector: '#pending-items', duration: 200 }); return
  }
  busy.value = true; error.value = ''
  try { await saveThenCommit(persistReport, () => commit()) }
  catch (e) { error.value = message(e) }
  finally { busy.value = false }
}
function viewReport() { if (success.value) uni.navigateTo({ url: '/pages/report-detail/index?id=' + encodeURIComponent(success.value.report_id) }) }
function done() { uni.reLaunch({ url: '/pages/index/index' }) }
</script>

<template>
  <view class="page">
    <view v-if="success" class="card">
      <text class="title">报告保存成功</text>
      <text>{{ success.item_count }} 项检验结果已保存</text>
      <button @click="viewReport">查看检验报告</button>
      <button @click="done">完成</button>
    </view>
    <text v-else-if="loading">正在加载确认进度...</text>
    <view v-else>
      <view v-if="error" class="card">
        <text class="error">{{ error }}</text>
        <button v-if="!workspace" @click="load">重新加载</button>
      </view>
      <view v-if="workspace">
        <text>原始检验报告始终是最终核对依据。</text>
        <view class="card">
          <text class="title">报告信息</text>
          <picker :range="profiles" range-key="display_name" :value="profileIndex" :disabled="busy" @change="changeProfile">
            <view>所属健康档案：{{ profileName }}（点击调整）</view>
          </picker>
          <text>医院（可空）</text><input v-model="report.hospital_name" :disabled="busy" placeholder="按原始报告填写" />
          <text>检验日期（必填）</text>
          <picker mode="date" :value="report.examination_date" :disabled="busy" @change="report.examination_date = $event.detail.value">
            <view class="field">{{ report.examination_date || '请选择报告上的检验日期' }}</view>
          </picker>
          <text>检验时间（可空）</text><input v-model="report.examination_time" :disabled="busy" placeholder="HH:MM 或 HH:MM:SS" />
          <text>报告编号（可空）</text><input v-model="report.report_no" :disabled="busy" />
          <text>报告分类（可空）</text><input v-model="report.report_category" :disabled="busy" />
          <button :disabled="busy" @click="saveReport">保存报告信息</button>
          <button v-for="asset in workspace.assets" :key="asset.id" @click="preview(asset.id)">核对第 {{ asset.page_no }} 页原图</button>
        </view>
        <view id="pending-items" class="card">
          <text class="title warning">待确认 {{ groups.pending.length }} 项</text>
          <text v-if="!groups.pending.length">待确认项目已全部处理。</text>
          <view v-for="item in groups.pending" :key="item.id" class="item">
            <text class="warning">待确认 · {{ item.metric_name || '名称待填写' }}</text>
            <text v-if="item.standard_metric_id">标准指标：{{ standardMetricLabel(item.standard_metric_id, item.standard_metric) }}</text>
            <text>{{ item.result_text || '结果待填写' }} {{ item.unit_normalized || item.unit_original }} · 参考：{{ item.reference_text || '无' }}</text>
            <button v-if="item.source" size="mini" @click="preview(item.source.asset_id)">查看来源第 {{ item.source.page_no }} 页</button>
            <button size="mini" :disabled="busy" @click="edit(item)">核对 / 修改 / 选择标准指标</button>
            <button size="mini" :disabled="busy || !item.standard_metric_id" @click="resolve(item, 'ACCEPTED')">确认正确</button>
            <text v-if="!item.standard_metric_id">请选择标准指标，或在编辑中按原名称保存。</text>
            <button size="mini" :disabled="busy" @click="resolve(item, 'REMOVED')">删除错误识别</button>
          </view>
        </view>
        <view class="card">
          <text class="title">已采用 {{ groups.adopted.length }} 项</text>
          <text>AUTO 默认采用，无需逐项确认；如有错误可主动修改。</text>
          <view v-for="item in groups.adopted" :key="item.id" class="item">
            <text>{{ item.metric_name }} · {{ item.result_text }} {{ item.unit_normalized || item.unit_original }}</text>
            <text v-if="item.standard_metric_id">标准指标：{{ standardMetricLabel(item.standard_metric_id, item.standard_metric) }}</text>
            <text>{{ item.source_type === 'OCR_AUTO' ? '自动采用' : item.source_type === 'MANUAL' ? '手工录入' : '人工核对' }}</text>
            <button size="mini" :disabled="busy" @click="edit(item)">编辑</button>
            <button size="mini" :disabled="busy" @click="resolve(item, 'REMOVED')">删除错误项</button>
          </view>
          <text v-if="!groups.adopted.length">暂无已采用项目，可添加漏识别项目。</text>
          <button :disabled="busy" @click="edit(null)">+ 添加漏识别项目</button>
        </view>
        <view v-if="groups.removed.length" class="card">
          <text>已移除 {{ groups.removed.length }} 项，不进入正式报告。</text>
          <view v-for="item in groups.removed" :key="item.id">
            <text>{{ item.metric_name }}</text><button size="mini" :disabled="busy" @click="edit(item)">重新核对</button>
          </view>
        </view>
        <view v-if="editing" id="item-editor" class="card">
          <text class="title">{{ selected ? '编辑检验项目' : '添加漏识别项目' }}</text>
          <button v-if="selected?.source" @click="preview(selected.source.asset_id)">核对来源原图</button>
          <text>指标名称</text><input v-model="form.metric_name" :disabled="busy" />
          <text>结果（支持文本结果）</text><input v-model="form.result_text" :disabled="busy" />
          <text>单位（可空）</text><input v-model="form.unit_original" :disabled="busy" />
          <text>参考范围（可空）</text><input v-model="form.reference_text" :disabled="busy" />
          <text>标准指标：{{ standardMetricLabel(form.standard_metric_id, selected?.standard_metric, metricNames) }}</text>
          <input v-model="metricQuery" :disabled="busy || searching" placeholder="输入标准名称或 code" />
          <button :disabled="busy || searching" @click="searchMetrics">{{ searching ? '查询中...' : '查询标准指标' }}</button>
          <text v-if="searched && !metrics.length">没有匹配的标准指标，可按原名称保存。</text>
          <button v-for="metric in metrics" :key="metric.id" size="mini" :disabled="busy" @click="form.standard_metric_id = metric.id">{{ metric.name }}（{{ metric.code }}）</button>
          <button :disabled="busy" @click="saveItem(false)">保存并完成核对</button>
          <button :disabled="busy" @click="saveItem(true)">按原名称保存（不关联标准指标）</button>
          <button :disabled="busy" @click="editing = false">取消编辑</button>
        </view>
        <text>最终保存表示已核对整份报告，包括默认采用的 AUTO 项。</text>
        <button :disabled="busy" :loading="busy" @click="submit">最终确认并保存</button>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page { padding: 28rpx; }
.card { display: flex; flex-direction: column; gap: 18rpx; padding: 24rpx; margin: 20rpx 0; background: #fff; border: 1px solid #ddd; border-radius: 12rpx; }
.item { display: flex; flex-direction: column; gap: 12rpx; padding: 20rpx 0; border-bottom: 1px solid #ddd; }
.title { font-size: 34rpx; font-weight: 600; }
.warning { color: #9a5200; font-weight: 600; }
.error { color: #b42318; }
input, .field { padding: 18rpx; min-height: 40rpx; border: 1px solid #ccc; border-radius: 8rpx; }
</style>
