<script setup lang="ts">
import { ref } from 'vue'
import { onHide, onLoad, onShow, onUnload } from '@dcloudio/uni-app'
import { ensureLogin, request, type Ingestion, type OcrStatus } from '../../api'

const id = ref('')
const state = ref<OcrStatus | null>(null)
const loading = ref(true)
const error = ref('')
const retrying = ref(false)
const manualizing = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
let visible = false

onLoad(params => { id.value = params?.id || '' })
onShow(() => { visible = true; load() })
onHide(stop)
onUnload(stop)
function stop() { visible = false; if (timer) clearTimeout(timer); timer = undefined }
function schedule() {
  if (timer) clearTimeout(timer)
  if (visible && ['QUEUED', 'PROCESSING'].includes(state.value?.ingestion_status || '')) {
    timer = setTimeout(load, 3000)
  }
}
async function load() {
  if (!id.value) { error.value = '任务编号缺失'; loading.value = false; return }
  try {
    const me = await ensureLogin()
    const ingestion = await request<Ingestion>(`/ingestions/${id.value}`)
    if (ingestion.health_profile_id !== me.default_health_profile_id) {
      error.value = '请切换回任务所属健康档案'; return
    }
    state.value = await request<OcrStatus>(`/ingestions/${id.value}/ocr`)
    error.value = ''
  } catch (e) { error.value = e instanceof Error ? e.message : '获取识别状态失败' }
  finally { loading.value = false; schedule() }
}
async function retry() {
  if (retrying.value || state.value?.ingestion_status !== 'OCR_FAILED') return
  retrying.value = true; error.value = ''
  try {
    state.value = await request<OcrStatus>(`/ingestions/${id.value}/ocr/retry`, 'POST')
    schedule()
  } catch (e) { error.value = e instanceof Error ? e.message : '重新识别失败' }
  finally { retrying.value = false }
}
function images() { uni.navigateTo({ url: `/pages/upload/index?id=${id.value}` }) }
function newTask() { uni.navigateTo({ url: '/pages/upload/index?new=1' }) }
function confirmation() { uni.navigateTo({ url: `/pages/confirmation/index?id=${id.value}` }) }
async function manual() {
  if (manualizing.value || retrying.value) return
  manualizing.value = true; error.value = ''
  try { await request(`/ingestions/${id.value}/manual`, 'POST'); confirmation() }
  catch (e) { error.value = e instanceof Error ? e.message : '转为手工录入失败' }
  finally { manualizing.value = false }
}
</script>

<template>
  <view class="page">
    <text v-if="loading">正在读取识别状态...</text>
    <text v-if="error" class="error">{{ error }}</text>
    <button v-if="error" @click="load">重新加载</button>
    <view v-if="state">
      <text v-if="state.ingestion_status === 'QUEUED'">已排队，等待识别。任务会在后台继续。</text>
      <text v-else-if="state.ingestion_status === 'PROCESSING'">正在识别，请稍后。这里显示的是服务端状态。</text>
      <view v-else-if="state.ingestion_status === 'PENDING_CONFIRMATION'">
        <text>识别完成，待确认</text>
        <text>共识别 {{ state.task?.result_summary?.total_count ?? 0 }} 项</text>
        <text>自动候选 {{ state.task?.result_summary?.auto_count ?? 0 }} 项</text>
        <text>待重点核对 {{ state.task?.result_summary?.review_count ?? 0 }} 项</text>
        <button @click="confirmation">确认检验结果</button>
      </view>
      <view v-else-if="state.ingestion_status === 'OCR_FAILED'">
        <text>识别失败，请重试或新建上传任务。</text>
        <text>错误码：{{ state.task?.error_code }}</text>
        <button :disabled="retrying || manualizing" @click="retry">重新识别</button>
        <button :disabled="retrying || manualizing" @click="manual">保留原图，转为手工录入</button>
        <button @click="newTask">重新上传报告</button>
      </view>
      <text v-else-if="state.ingestion_status === 'CONFIRMED'">报告已保存</text>
      <button @click="images">查看原图</button>
    </view>
  </view>
</template>

<style scoped>
.page { padding: 32rpx; display: flex; flex-direction: column; gap: 20rpx; }
.page view { display: flex; flex-direction: column; gap: 16rpx; }
.error { color: #b42318; }
</style>
