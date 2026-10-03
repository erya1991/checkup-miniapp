<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ApiError, ensureLogin, request, type Asset, type Ingestion, type Profile } from '../../api'
import { confirmationErrorMessages, confirmationFormErrors, confirmationIdentityHint, confirmationItemLabel,
  groupedItems, itemForm, itemPayload, saveThenCommit, standardMetricLabel,
  type ConfirmationItem, type ItemForm, type StandardMetric } from '../../confirmation'
import { openReports } from '../../navigation'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import StatusTag from '../../components/StatusTag.vue'

interface Workspace {
  id: string; status: string; mode: string; health_profile_id: string; health_profile: Profile
  hospital_name: string | null; examination_date: string | null; examination_time: string | null
  report_no: string | null; report_category: string | null
  assets: Asset[]; items: ConfirmationItem[]; pending_count: number
}
interface CommitResult { report_id: string; status: string; item_count: number }
interface DuplicateSummary { hospital_name: string | null; examination_date: string; report_no: string | null; item_count: number }
class ValidationError extends Error {}

const id = ref('')
const workspace = ref<Workspace | null>(null)
const profiles = ref<Profile[]>([])
const loading = ref(true)
const busy = ref(false)
const operation = ref('')
const error = ref('')
const success = ref<CommitResult | null>(null)
const editing = ref(false)
const adoptedExpanded = ref(false)
const removedExpanded = ref(false)
const selected = ref<ConfirmationItem | null>(null)
const form = reactive<ItemForm>(itemForm(null))
const itemErrors = reactive({ metric_name: '', result_text: '', standard_metric_id: '' })
const reportErrors = reactive({ examination_date: '', examination_time: '' })
const metricQuery = ref('')
const metrics = ref<StandardMetric[]>([])
const metricNames = ref<Record<string, string>>({})
const searching = ref(false)
const searched = ref(false)
const previewLoading = ref('')
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
watch(() => form.metric_name, () => { itemErrors.metric_name = '' }, { flush: 'sync' })
watch(() => form.result_text, () => { itemErrors.result_text = '' }, { flush: 'sync' })
watch(() => form.standard_metric_id, () => { itemErrors.standard_metric_id = '' }, { flush: 'sync' })
watch(() => report.examination_date, () => { reportErrors.examination_date = '' }, { flush: 'sync' })
watch(() => report.examination_time, () => { reportErrors.examination_time = '' }, { flush: 'sync' })

function message(e: unknown) {
  if (e instanceof ValidationError) return e.message
  if (e instanceof ApiError) {
    if (e.code === 'INVALID_REPORT_DATE') {
      reportErrors.examination_date = '请检查是否与报告上的检验日期一致。'
      reportErrors.examination_time = '请留空，或填写有效的 HH:MM / HH:MM:SS。'
    }
    if (e.code === 'STANDARD_METRIC_NOT_FOUND') itemErrors.standard_metric_id = '请重新选择关联指标，或按报告原名称保存。'
    return confirmationErrorMessages[e.code] || userError(e, '操作未完成，请检查网络后重试。')
  }
  return userError(e, '操作未完成，请检查网络后重试。')
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
    if (!id.value) throw new ValidationError('缺少报告信息，请返回待处理报告重新打开。')
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
  if (!report.examination_date) {
    reportErrors.examination_date = '请选择原始报告上的检验日期，不能用上传日期代替。'
    throw new ValidationError('请填写报告上的检验日期，不能使用上传日期代替。')
  }
  const value = await request<Workspace>(`/ingestions/${id.value}/confirmation`, 'PUT', {
    ...report, hospital_name: report.hospital_name.trim() || null,
    examination_time: report.examination_time.trim() || null,
    report_no: report.report_no.trim() || null, report_category: report.report_category.trim() || null,
  })
  applyWorkspace(value)
}
async function saveReport() {
  if (busy.value) return
  busy.value = true; operation.value = 'report'; error.value = ''
  try { await persistReport(); uni.showToast({ title: '报告信息已保存', icon: 'success' }) }
  catch (e) { error.value = message(e) }
  finally { busy.value = false; operation.value = '' }
}
async function preview(assetId?: string) {
  const target = assetId || workspace.value?.assets[0]?.id
  if (!target || previewLoading.value || busy.value) return
  previewLoading.value = target; error.value = ''
  try {
    const signed = await request<{ url: string }>(`/ingestions/${id.value}/assets/${target}/preview`)
    previewing = true
    await uni.previewImage({ current: signed.url, urls: [signed.url] })
  } catch (e) { previewing = false; error.value = message(e) }
  finally { previewLoading.value = '' }
}
async function edit(item: ConfirmationItem | null) {
  if (busy.value) return
  selected.value = item; Object.assign(form, itemForm(item)); editing.value = true
  Object.assign(itemErrors, { metric_name: '', result_text: '', standard_metric_id: '' })
  metrics.value = []; metricQuery.value = ''; searched.value = false; error.value = ''
  await nextTick()
  uni.pageScrollTo({ selector: '#item-editor', duration: 200 })
}
async function searchMetrics() {
  if (searching.value || busy.value) return
  searching.value = true; error.value = ''
  try {
    metrics.value = await request<StandardMetric[]>(`/standard-metrics?q=${encodeURIComponent(metricQuery.value)}`)
    for (const metric of metrics.value) metricNames.value[metric.id] = metric.name
    searched.value = true
  } catch (e) { error.value = message(e) }
  finally { searching.value = false }
}
async function saveItem(keepOriginal = false) {
  if (busy.value) return
  Object.assign(itemErrors, confirmationFormErrors(form), { standard_metric_id: '' })
  if (itemErrors.metric_name || itemErrors.result_text) {
    error.value = '请补全标记的指标名称和结果，再保存此项。'
    return
  }
  busy.value = true; operation.value = 'item'; error.value = ''
  try {
    const payload = itemPayload(form, selected.value, keepOriginal)
    const path = `/ingestions/${id.value}/confirmation/items${selected.value ? '/' + selected.value.id : ''}`
    const value = await request<Workspace>(path, selected.value ? 'PUT' : 'POST', payload)
    // Report inputs may be unsaved; item editing must not erase them.
    workspace.value = value; editing.value = false
    uni.showToast({ title: '项目已保存', icon: 'success' })
  } catch (e) { error.value = message(e) }
  finally { busy.value = false; operation.value = '' }
}
async function resolve(item: ConfirmationItem, resolution: 'ACCEPTED' | 'REMOVED') {
  if (busy.value) return
  busy.value = true; operation.value = 'resolve'; error.value = ''
  try {
    if (resolution === 'REMOVED') {
      const choice = await uni.showModal({ title: '移除错误项目', content: '此项不进入正式报告，原图和原始识别记录仍保留。',
        confirmText: '移除此项', cancelText: '保留' })
      if (!choice.confirm) return
    }
    workspace.value = await request<Workspace>(`/ingestions/${id.value}/confirmation/items/${item.id}`, 'PUT', { resolution })
    uni.showToast({ title: resolution === 'REMOVED' ? '项目已移除' : '核对完成', icon: 'success' })
  } catch (e) { error.value = message(e) }
  finally { busy.value = false; operation.value = '' }
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
    error.value = `还有 ${groups.value.pending.length} 项需要核对，请先核对。`
    uni.pageScrollTo({ selector: '#pending-items', duration: 200 }); return
  }
  busy.value = true; operation.value = 'commit'; error.value = ''
  try { await saveThenCommit(persistReport, () => commit()) }
  catch (e) {
    error.value = message(e)
    if (reportErrors.examination_date) uni.pageScrollTo({ selector: '#report-information', duration: 200 })
  }
  finally { busy.value = false; operation.value = '' }
}
function cancelEdit() { if (!busy.value) { editing.value = false; error.value = '' } }
function viewReport() { if (success.value) uni.navigateTo({ url: '/pages/report-detail/index?id=' + encodeURIComponent(success.value.report_id) }) }
function done() { openReports() }
</script>

<template>
  <PageContainer>
    <view v-if="success" class="card success-card">
      <StatusTag tone="success" label="已保存" />
      <text class="title">报告保存成功</text>
      <text>{{ success.item_count }} 项检验结果已加入正式报告。</text>
      <text class="muted">可查看报告，也可回到报告列表继续整理。</text>
      <button class="primary" @click="viewReport">查看检验报告</button>
      <button class="secondary" @click="done">返回报告列表</button>
    </view>
    <UiState v-else-if="loading" type="loading" title="正在加载核对进度" description="正在读取这份报告已保存的核对结果。" />
    <view v-else class="confirmation-content">
      <UiState v-if="!workspace" type="error" title="暂时无法打开报告" :description="error" action="重新加载" @action="load" />
      <button v-if="!workspace" class="secondary" @click="done">返回报告列表</button>
      <view v-if="workspace" class="confirmation-content">
        <view class="confirmation-heading">
          <text class="title">核对报告</text>
          <view class="process" aria-label="当前处于核对结果，报告尚未保存">
            <text class="muted">上传完成</text>
            <text class="muted">{{ workspace.mode === 'MANUAL' ? '手工录入' : '识别完成' }}</text>
            <text class="current-step">核对结果</text>
            <text class="muted">保存报告</text>
          </view>
          <StatusTag :tone="groups.pending.length ? 'warning' : 'success'"
            :label="groups.pending.length ? '还有 ' + groups.pending.length + ' 项需要核对' : '需要核对的项目已处理'" />
          <text class="muted">报告尚未正式保存。请核对基本信息和检验结果，最后确认整份报告。</text>
          <text v-if="error" class="error" role="alert">{{ error }}</text>
        </view>

        <view class="card">
          <text class="section-title">对照原始报告</text>
          <text class="muted">原始检验报告始终是最终核对依据。</text>
          <view class="actions">
            <button v-for="asset in workspace.assets" :key="asset.id" class="secondary"
              :disabled="busy || !!previewLoading" :loading="previewLoading === asset.id" @click="preview(asset.id)">
              查看第 {{ asset.page_no }} 页原图
            </button>
          </view>
          <text v-if="!workspace.assets.length" class="muted">未找到原始图片，请重新加载核对。</text>
        </view>

        <view id="report-information" class="card">
          <text class="section-title">报告基本信息</text>
          <text class="muted">检验日期必填，其余信息可按报告补充。</text>
          <view class="form-row">
            <text class="label">所属健康档案</text>
            <picker :range="profiles" range-key="display_name" :value="profileIndex" :disabled="busy" @change="changeProfile">
              <view class="field">{{ profileName }} ▾</view>
            </picker>
            <text class="muted">保存前可调整报告所属的家人。</text>
          </view>
          <view class="form-row">
            <text class="label">医院（可选）</text>
            <input v-model="report.hospital_name" class="field" :disabled="busy" placeholder="按原始报告填写" />
          </view>
          <view class="form-row">
            <text class="label">检验日期（必填）</text>
            <picker mode="date" :value="report.examination_date" :disabled="busy" @change="report.examination_date = $event.detail.value">
              <view class="field" :class="{ 'field-invalid': reportErrors.examination_date }">{{ report.examination_date || '请选择报告上的检验日期' }}</view>
            </picker>
            <text v-if="reportErrors.examination_date" class="error">{{ reportErrors.examination_date }}</text>
          </view>
          <view class="form-row">
            <text class="label">检验时间（可选）</text>
            <input v-model="report.examination_time" class="field" :class="{ 'field-invalid': reportErrors.examination_time }"
              :disabled="busy" placeholder="HH:MM 或 HH:MM:SS" />
            <text v-if="reportErrors.examination_time" class="error">{{ reportErrors.examination_time }}</text>
          </view>
          <view class="form-row">
            <text class="label">报告编号（可选）</text>
            <input v-model="report.report_no" class="field" :disabled="busy" placeholder="按原始报告填写" />
          </view>
          <view class="form-row">
            <text class="label">报告分类（可选）</text>
            <input v-model="report.report_category" class="field" :disabled="busy" placeholder="如血常规、肝功能" />
          </view>
          <button class="secondary" :disabled="busy" :loading="operation === 'report'" @click="saveReport">保存基本信息</button>
        </view>

        <view id="pending-items" class="card pending-card">
          <view class="section-heading">
            <text class="section-title">需要核对 · {{ groups.pending.length }} 项</text>
            <StatusTag v-if="groups.pending.length" tone="warning" label="请优先处理" />
          </view>
          <text v-if="!groups.pending.length" class="muted">需要核对的项目已全部处理，请继续检查已采用结果。</text>
          <view v-for="item in groups.pending" :key="item.id" class="confirmation-item">
            <view class="section-heading">
              <text class="section-title">{{ item.metric_name || '指标名称待填写' }}</text>
              <StatusTag tone="warning" :label="confirmationItemLabel(item)" />
            </view>
            <text class="result">{{ item.result_text || '结果待填写' }} {{ item.unit_normalized || item.unit_original }}</text>
            <text class="muted">参考范围：{{ item.reference_text || '报告未提供' }}</text>
            <text v-if="item.standard_metric_id" class="muted">关联指标：{{ standardMetricLabel(item.standard_metric_id, item.standard_metric) }}</text>
            <text v-if="confirmationIdentityHint(item)" class="muted">{{ confirmationIdentityHint(item) }}</text>
            <view class="actions">
              <button class="secondary" :disabled="busy" @click="edit(item)">核对 / 修改</button>
              <button class="text-action" :disabled="busy || !item.standard_metric_id" @click="resolve(item, 'ACCEPTED')">确认正确</button>
            </view>
            <view class="actions">
              <button v-if="item.source" class="text-action" :disabled="busy || !!previewLoading"
                @click="preview(item.source.asset_id)">对照第 {{ item.source.page_no }} 页</button>
              <button class="danger" :disabled="busy" @click="resolve(item, 'REMOVED')">移除错误项目</button>
            </view>
          </view>
        </view>

        <view class="card">
          <button class="text-action collapse-toggle" :disabled="busy" @click="adoptedExpanded = !adoptedExpanded">
            <text class="section-title">已采用 · {{ groups.adopted.length }} 项</text>
            <text class="muted">{{ adoptedExpanded ? '收起' : '展开查看 / 编辑' }}</text>
          </button>
          <text class="muted">自动采用的项目无需逐项确认，仍可展开查看并主动修改。</text>
          <view v-if="adoptedExpanded">
            <view v-for="item in groups.adopted" :key="item.id" class="confirmation-item">
              <view class="section-heading">
                <text class="section-title">{{ item.metric_name }}</text>
                <StatusTag :tone="item.source_type === 'OCR_AUTO' ? 'success' : 'neutral'" :label="confirmationItemLabel(item)" />
              </view>
              <text class="result">{{ item.result_text }} {{ item.unit_normalized || item.unit_original }}</text>
              <text class="muted">参考范围：{{ item.reference_text || '报告未提供' }}</text>
              <text v-if="item.standard_metric_id" class="muted">关联指标：{{ standardMetricLabel(item.standard_metric_id, item.standard_metric) }}</text>
              <text v-if="confirmationIdentityHint(item)" class="muted">{{ confirmationIdentityHint(item) }}</text>
              <view class="actions">
                <button class="secondary" :disabled="busy" @click="edit(item)">修改此项</button>
                <button v-if="item.source" class="text-action" :disabled="busy || !!previewLoading"
                  @click="preview(item.source.asset_id)">对照原图</button>
                <button class="danger" :disabled="busy" @click="resolve(item, 'REMOVED')">移除错误项目</button>
              </view>
            </view>
          </view>
          <text v-if="!groups.adopted.length" class="muted">暂无已采用项目。报告有漏识别内容时可手工补充。</text>
          <button class="secondary" :disabled="busy" @click="edit(null)">添加漏识别项目</button>
        </view>

        <view v-if="groups.removed.length" class="card">
          <button class="text-action collapse-toggle" :disabled="busy" @click="removedExpanded = !removedExpanded">
            <text class="section-title">已移除 · {{ groups.removed.length }} 项</text>
            <text class="muted">{{ removedExpanded ? '收起' : '展开查看' }}</text>
          </button>
          <text class="muted">这些项目不进入正式报告，原始识别事实仍保留，可重新核对。</text>
          <view v-if="removedExpanded">
            <view v-for="item in groups.removed" :key="item.id" class="confirmation-item">
              <text>{{ item.metric_name }} · {{ item.result_text }}</text>
              <button class="secondary" :disabled="busy" @click="edit(item)">重新核对</button>
            </view>
          </view>
        </view>

        <view v-if="editing" id="item-editor" class="card">
          <text class="section-title">{{ selected ? '核对检验项目' : '添加漏识别项目' }}</text>
          <text v-if="error" class="error" role="alert">{{ error }}</text>
          <button v-if="selected?.source" class="secondary" :disabled="busy || !!previewLoading"
            @click="preview(selected.source.asset_id)">对照来源原图</button>
          <view class="form-row">
            <text class="label">指标名称（必填）</text>
            <input v-model="form.metric_name" class="field" :class="{ 'field-invalid': itemErrors.metric_name }" :disabled="busy" placeholder="报告上的指标名称" />
            <text v-if="itemErrors.metric_name" class="error">{{ itemErrors.metric_name }}</text>
          </view>
          <view class="form-row">
            <text class="label">结果（必填，支持文本）</text>
            <input v-model="form.result_text" class="field" :class="{ 'field-invalid': itemErrors.result_text }" :disabled="busy" placeholder="数字、阴性、阳性等报告原文" />
            <text v-if="itemErrors.result_text" class="error">{{ itemErrors.result_text }}</text>
          </view>
          <view class="form-row">
            <text class="label">单位（可选）</text>
            <input v-model="form.unit_original" class="field" :disabled="busy" placeholder="按报告填写" />
          </view>
          <view class="form-row">
            <text class="label">参考范围（可选）</text>
            <input v-model="form.reference_text" class="field" :disabled="busy" placeholder="仅填写本次报告的参考范围" />
          </view>
          <view class="form-row">
            <text class="label">关联指标</text>
            <text>{{ standardMetricLabel(form.standard_metric_id, selected?.standard_metric, metricNames) }}</text>
            <text class="muted">关联后，可在“我的指标”查看同类检验结果与趋势。</text>
            <input v-model="metricQuery" class="field" :class="{ 'field-invalid': itemErrors.standard_metric_id }"
              :disabled="busy || searching" placeholder="输入指标名称或缩写" @confirm="searchMetrics" />
            <text v-if="itemErrors.standard_metric_id" class="error">{{ itemErrors.standard_metric_id }}</text>
            <button class="secondary" :disabled="busy || searching" :loading="searching" @click="searchMetrics">搜索关联指标</button>
            <text v-if="searched && !metrics.length" class="muted">没有找到匹配指标，可以按报告原名称保存。</text>
            <button v-for="metric in metrics" :key="metric.id" class="secondary metric-option"
              :disabled="busy" @click="form.standard_metric_id = metric.id">
              <text>{{ metric.name }}</text><text class="muted">{{ metric.code }}{{ form.standard_metric_id === metric.id ? ' · 已选择' : '' }}</text>
            </button>
          </view>
          <button class="primary" :disabled="busy" :loading="operation === 'item'" @click="saveItem(false)">保存此项并完成核对</button>
          <text class="muted">若不关联指标，可以按报告原名称保存；该项不参与“我的指标”趋势。</text>
          <button class="secondary" :disabled="busy" @click="saveItem(true)">按报告原名称保存</button>
          <button class="text-action" :disabled="busy" @click="cancelEdit">取消编辑</button>
        </view>

        <view v-if="!editing" class="sticky-action">
          <text v-if="groups.pending.length" class="muted">请先完成 {{ groups.pending.length }} 项核对，再保存整份报告。</text>
          <text v-else class="muted">最终保存表示已核对整份报告，包括自动采用的项目。</text>
          <text v-if="error" class="error" role="alert">{{ error }}</text>
          <button class="primary" :disabled="busy" :loading="operation === 'commit'" @click="submit">确认并保存报告</button>
        </view>
      </view>
    </view>
  </PageContainer>
</template>

<style scoped>
.confirmation-content, .confirmation-heading { display: flex; flex-direction: column; gap: var(--page-gap); }
.confirmation-heading { gap: 16rpx; }
.process { display: flex; flex-wrap: wrap; gap: 12rpx 24rpx; align-items: center; }
.current-step { color: var(--primary-text); font-size: var(--font-note); font-weight: 600; }
.form-row { display: flex; flex-direction: column; gap: 12rpx; }
.field-invalid { border-color: var(--danger); }
.pending-card { border-color: var(--warning); }
.confirmation-item { display: flex; flex-direction: column; gap: 12rpx; padding: 24rpx 0; border-top: 1rpx solid var(--border); }
.result { font-weight: 600; font-size: var(--font-section); }
.collapse-toggle { display: flex; flex-wrap: wrap; justify-content: space-between; width: 100%; gap: 12rpx; text-align: left; padding: 12rpx 0 !important; }
.metric-option { display: flex; flex-direction: column; align-items: flex-start; width: 100%; text-align: left; }
.sticky-action { display: flex; flex-direction: column; gap: 12rpx; }
</style>
