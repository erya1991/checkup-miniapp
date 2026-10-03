<script setup lang="ts">
import { ref } from 'vue'
import { onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import { ensureLogin, request, type Ingestion, type OcrStatus } from '../../api'
import { requestGuard } from '../../profile-metrics'
import { userError } from '../../ui'
import { navigate, newUploadPath, openReports } from '../../navigation'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import StatusTag from '../../components/StatusTag.vue'
const id = ref(''), state = ref<OcrStatus | null>(null), loading = ref(true), error = ref('')
const retrying = ref(false), manualizing = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
let visible = false
const guard = requestGuard()
onLoad(params => { id.value = params?.id || '' })
onShow(() => { visible = true; state.value = null; loading.value = true; load() })
onHide(stop); onUnload(stop)
function stop() { visible = false; guard.invalidate(); if (timer) clearTimeout(timer); timer = undefined }
function schedule() {
  if (timer) clearTimeout(timer)
  if (visible && !error.value && ['QUEUED', 'PROCESSING'].includes(state.value?.ingestion_status || '')) timer = setTimeout(load, 3000)
}
async function load() {
  const run = guard.next()
  if (!id.value) { error.value = '无法找到这份报告，请返回待处理报告列表。'; loading.value = false; return }
  try {
    const me = await ensureLogin()
    const ingestion = await request<Ingestion>(`/ingestions/${id.value}`)
    if (!guard.current(run)) return
    if (ingestion.health_profile_id !== me.default_health_profile_id) { error.value = '请切换回这份报告所属的健康档案。'; state.value = null; return }
    const value = await request<OcrStatus>(`/ingestions/${id.value}/ocr`)
    if (!guard.current(run)) return
    state.value = value; error.value = ''
  } catch (e) { if (guard.current(run)) error.value = userError(e, '暂时无法获取识别状态，请重试。') }
  finally { if (guard.current(run)) { loading.value = false; schedule() } }
}
async function retry() {
  if (retrying.value || manualizing.value || state.value?.ingestion_status !== 'OCR_FAILED') return
  retrying.value = true; error.value = ''
  const run = guard.next()
  try {
    const value = await request<OcrStatus>(`/ingestions/${id.value}/ocr/retry`, 'POST')
    if (guard.current(run)) { state.value = value; schedule() }
  } catch (e) { if (guard.current(run)) error.value = userError(e, '未能重新识别，请重试。') }
  finally { retrying.value = false }
}
async function images() {
  if (!state.value || ['UPLOADING', 'READY'].includes(state.value.ingestion_status)) {
    navigate(`/pages/upload/index?id=${encodeURIComponent(id.value)}`); return
  }
  try {
    const ingestion = await request<Ingestion>(`/ingestions/${encodeURIComponent(id.value)}`)
    const signed = await Promise.all(ingestion.assets.map(asset => request<{ url: string }>(`/ingestions/${encodeURIComponent(id.value)}/assets/${encodeURIComponent(asset.id)}/preview`)))
    const urls = signed.map(image => image.url)
    if (!urls.length) { error.value = '这份报告没有可查看的原始图片。'; return }
    await uni.previewImage({ current: urls[0], urls })
  } catch (e) { error.value = userError(e, '原图暂时无法加载，请重试。') }
}
function confirmation() { uni.redirectTo({ url: `/pages/confirmation/index?id=${encodeURIComponent(id.value)}` }) }
async function manual() {
  if (manualizing.value || retrying.value || state.value?.ingestion_status !== 'OCR_FAILED') return
  manualizing.value = true; error.value = ''
  try { await request(`/ingestions/${id.value}/manual`, 'POST'); if (visible) confirmation() }
  catch (e) { error.value = userError(e, '未能进入手工录入，请重试。') }
  finally { manualizing.value = false }
}
</script>
<template>
  <PageContainer>
    <UiState v-if="loading" type="loading" title="正在获取识别状态" />
    <UiState v-else-if="error" type="error" title="暂时无法获取状态" :description="error" action="重试" @action="load" />
    <template v-else-if="state">
      <text class="muted">上传 → 识别 → 核对 → 正式保存</text>
      <view class="card">
        <template v-if="['QUEUED', 'PROCESSING'].includes(state.ingestion_status)">
          <StatusTag :label="state.ingestion_status === 'QUEUED' ? '等待识别' : '正在识别'" />
          <text class="title">{{ state.ingestion_status === 'QUEUED' ? '报告等待识别' : '正在读取报告内容' }}</text>
          <text class="muted">可以离开这个页面，报告会在后台继续识别。稍后从首页的待处理报告继续核对。</text>
          <button class="secondary" @click="navigate('/pages/index/index')">回到首页</button>
        </template>
        <template v-else-if="state.ingestion_status === 'PENDING_CONFIRMATION'">
          <StatusTag label="识别完成，等待核对" tone="warning" />
          <text class="title">核对后才能保存报告</text>
          <text class="muted">这份报告尚未正式保存。请对照原图核对识别结果，再确认保存。</text>
          <text v-if="state.task?.result_summary">初次识别出 {{ state.task.result_summary.total_count }} 项</text>
          <button class="primary" @click="confirmation">核对报告</button>
        </template>
        <template v-else-if="state.ingestion_status === 'OCR_FAILED'">
          <StatusTag label="识别失败" tone="warning" />
          <text class="title">报告暂时未能识别</text>
          <text class="muted">原图仍保留。你可以重新识别，或保留原图并手工录入检验项目。</text>
          <button class="primary" :loading="retrying" :disabled="retrying || manualizing" @click="retry">重新识别</button>
          <button class="secondary" :loading="manualizing" :disabled="retrying || manualizing" @click="manual">保留原图，手工录入</button>
          <button class="text-action" @click="navigate(newUploadPath())">上传另一份报告</button>
        </template>
        <template v-else-if="state.ingestion_status === 'CONFIRMED'">
          <StatusTag label="报告已保存" tone="success" /><text class="title">正式报告已保存</text>
          <button class="primary" @click="openReports()">查看检验报告</button>
        </template>
        <template v-else><text>图片上传尚未完成识别。</text><button class="primary" @click="images">继续上传</button></template>
      </view>
      <button class="text-action" @click="images">查看原始报告</button>
    </template>
  </PageContainer>
</template>
