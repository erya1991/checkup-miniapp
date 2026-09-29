<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, type Ingestion, type Profile } from '../../api'
import { ingestionTasksPath, taskDestination, taskStatusLabels } from '../../ingestion-tasks'

const profile = ref<Profile | null>(null)
const tasks = ref<Ingestion[]>([])
const loading = ref(true)
const error = ref('')
let loadVersion = 0

onShow(load)
async function load() {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  profile.value = null
  tasks.value = []
  try {
    const me = await ensureLogin()
    if (!me.default_health_profile_id) return
    const selectedProfile = await request<Profile>(`/health-profiles/${me.default_health_profile_id}`)
    const selectedTasks = await request<Ingestion[]>(ingestionTasksPath(me.default_health_profile_id))
    if (version === loadVersion) {
      profile.value = selectedProfile
      tasks.value = selectedTasks
    }
  } catch (e) {
    if (version === loadVersion) error.value = e instanceof Error ? e.message : '任务加载失败'
  } finally { if (version === loadVersion) loading.value = false }
}
function open(task: Ingestion) {
  const url = taskDestination(task)
  if (url) uni.navigateTo({ url })
}
function createdAt(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}
function navigate(url: string) { uni.navigateTo({ url }) }
</script>

<template>
  <view class="page">
    <text class="title">识别任务记录</text>
    <text v-if="loading">正在加载任务...</text>
    <view v-else-if="error">
      <text class="error">{{ error }}</text>
      <button @click="load">重试</button>
    </view>
    <view v-else-if="!profile">
      <text>请先选择健康档案。</text>
      <button @click="navigate('/pages/profiles/index')">选择档案</button>
    </view>
    <view v-else>
      <text>当前档案：{{ profile.display_name }}</text>
      <button @click="navigate('/pages/profiles/index')">切换档案</button>
      <text v-if="!tasks.length">该档案暂无识别任务。</text>
      <view v-for="task in tasks" :key="task.id" class="task">
        <text>创建时间：{{ createdAt(task.created_at) }}</text>
        <text>图片：{{ task.assets.length }} 张</text>
        <text>状态：{{ taskStatusLabels[task.status] || task.status }}</text>
        <text v-if="task.result_summary">
          识别 {{ task.result_summary.total_count }} 项 · 自动 {{ task.result_summary.auto_count }} 项 · 待核对 {{ task.result_summary.review_count }} 项
        </text>
        <button v-if="taskDestination(task)" size="mini" @click="open(task)">打开任务</button>
      </view>
    </view>
  </view>
</template>

<style scoped>
.page { padding: 36rpx; display: flex; flex-direction: column; gap: 20rpx; }
.title { font-size: 38rpx; font-weight: 600; }
.task { display: flex; flex-direction: column; gap: 12rpx; padding: 24rpx; margin-top: 20rpx; border: 1px solid #ddd; border-radius: 12rpx; }
.error { color: #b42318; }
</style>
