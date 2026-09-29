<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, type Ingestion, type Profile } from '../../api'

const loading = ref(true)
const error = ref('')
const current = ref<Profile | null>(null)
const draft = ref<Ingestion | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const me = await ensureLogin()
    const profiles = await request<Profile[]>('/health-profiles')
    current.value = profiles.find(p => p.id === me.default_health_profile_id) || profiles[0] || null
    const ingestions = await request<Ingestion[]>('/ingestions')
    draft.value = ingestions.find(i => i.health_profile_id === current.value?.id) || null
  } catch (e) { error.value = e instanceof Error ? e.message : '加载失败' }
  finally { loading.value = false }
}
onShow(load)

function navigate(url: string) { uni.navigateTo({ url }) }
function upload() {
  if (!current.value) return navigate('/pages/profile-edit/index')
  if (draft.value && ['QUEUED', 'PROCESSING', 'PENDING_CONFIRMATION', 'OCR_FAILED'].includes(draft.value.status)) {
    return navigate(`/pages/ocr/index?id=${draft.value.id}`)
  }
  navigate(`/pages/upload/index${draft.value ? `?id=${draft.value.id}` : ''}`)
}
</script>

<template>
  <view class="page">
    <text class="title">检查单</text>
    <text v-if="loading">正在登录和加载...</text>
    <view v-else-if="error">
      <text>登录或加载失败：{{ error }}</text>
      <button @click="load">重试</button>
    </view>
    <view v-else-if="!current">
      <text>还没有健康档案，请先创建本人档案。</text>
      <button @click="navigate('/pages/profile-edit/index')">创建本人档案</button>
    </view>
    <view v-else>
      <text>当前档案：{{ current.display_name }}</text>
      <button @click="navigate('/pages/profiles/index')">切换/管理档案</button>
      <button @click="navigate('/pages/ingestion-tasks/index')">识别任务记录</button>
      <button @click="upload">{{ draft && !['UPLOADING', 'READY'].includes(draft.status) ? '查看识别状态' : draft ? '继续上传报告' : '上传报告' }}</button>
      <button v-if="draft" @click="navigate('/pages/upload/index?new=1')">新建另一份上传任务</button>
      <text v-if="draft">当前导入任务：{{ draft.status }}，{{ draft.assets.length }} 张图片</text>
    </view>
  </view>
</template>

<style scoped>
.page { padding: 40rpx; display: flex; flex-direction: column; gap: 24rpx; }
.title { font-size: 42rpx; font-weight: 600; }
</style>
