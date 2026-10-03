<script setup lang="ts">
import { ref } from 'vue'
import { onShow, onHide } from '@dcloudio/uni-app'
import { ensureLogin, request, type Ingestion, type Profile } from '../../api'
import { ingestionTasksPath, taskDestination, taskStatusLabels } from '../../ingestion-tasks'

import { unfinished } from '../../reports'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import ProfileContext from '../../components/ProfileContext.vue'
import StatusTag from '../../components/StatusTag.vue'
import { newUploadPath, navigate } from '../../navigation'

const profile = ref<Profile | null>(null)
const tasks = ref<Ingestion[]>([])
const loading = ref(true)
const error = ref('')
let loadVersion = 0

onShow(load)
onHide(() => { ++loadVersion })
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
      tasks.value = selectedTasks.filter(t => unfinished(t.status))
    }
  } catch (e) {
    if (version === loadVersion) error.value = userError(e)
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
</script>

<template>
  <PageContainer>
    <UiState v-if="loading" type="loading" title="正在加载待处理报告" />
    <UiState v-else-if="error" type="error" title="暂时无法加载" :description="error" action="重试" @action="load" />
    <UiState v-else-if="!profile" type="empty" title="还没有健康档案" description="创建档案后，可以上传检验报告。" action="创建本人档案" @action="navigate('/pages/profile-edit/index')" />
    <template v-else>
      <ProfileContext :name="profile.display_name" @choose="navigate('/pages/profiles/index')" />
      <text class="title">待处理报告</text>
      <text class="muted">这些报告还未正式保存，请继续上传、识别或核对。</text>
      <UiState v-if="!tasks.length" type="empty" title="没有待处理报告" description="已保存的报告在“报告”中查看，也可以上传新的报告。" action="上传检验报告" @action="navigate(newUploadPath())" />
      <view v-for="task in tasks" :key="task.id" class="card" @click="open(task)">
        <StatusTag :label="taskStatusLabels[task.status] || '待处理'" :tone="['PENDING_CONFIRMATION', 'OCR_FAILED'].includes(task.status) ? 'warning' : 'neutral'" />
        <text class="section-title">{{ task.assets.length }} 页报告图片</text>
        <text class="muted">创建于 {{ createdAt(task.created_at) }}</text>
        <text v-if="task.result_summary" class="muted">初次识别出 {{ task.result_summary.total_count }} 项 · 请进入核对页查看当前进度</text>
        <button v-if="taskDestination(task)" class="secondary" @click.stop="open(task)">{{ task.status === 'PENDING_CONFIRMATION' ? '核对报告' : task.status === 'UPLOADING' || task.status === 'READY' ? '继续上传' : '查看识别状态' }}</button>
      </view>
    </template>
  </PageContainer>
</template>
