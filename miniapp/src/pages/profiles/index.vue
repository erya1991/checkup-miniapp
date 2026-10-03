<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { deleteWithConfirmation, profileContext, type DeletionImpact, type ProfileContext } from '../../profile-deletion'

const profiles = ref<Profile[]>([])
const selected = ref('')
const loading = ref(true)
const error = ref('')
const deleting = ref(false)
async function context() {
  const me = await ensureLogin()
  const rows = await request<Profile[]>('/health-profiles')
  return profileContext(rows, me.default_health_profile_id)
}
function applyContext(next: ProfileContext) {
  profiles.value = next.profiles; selected.value = next.selected
}
async function load() {
  loading.value = true; error.value = ''
  try {
    applyContext(await context())
  } catch (e) { error.value = e instanceof Error ? e.message : '加载失败' }
  finally { loading.value = false }
}
onShow(load)
function edit(id?: string) { uni.navigateTo({ url: `/pages/profile-edit/index${id ? `?id=${id}` : ''}` }) }
async function choose(id: string) {
  try {
    await request('/me/default-health-profile', 'PUT', { health_profile_id: id })
    selected.value = id
    uni.navigateBack()
  } catch (e) { uni.showToast({ title: e instanceof Error ? e.message : '切换失败', icon: 'none' }) }
}
async function remove(id: string) {
  if (deleting.value) return
  deleting.value = true
  try {
    const result = await deleteWithConfirmation(id, {
      impact: () => request<DeletionImpact>(`/health-profiles/${encodeURIComponent(id)}/deletion-impact`),
      confirm: async content => !!(await uni.showModal({ title: '永久删除档案', content, confirmText: '永久删除', confirmColor: '#c62828' })).confirm,
      remove: () => request(`/health-profiles/${encodeURIComponent(id)}`, 'DELETE'),
      reload: context,
      apply: applyContext,
      notify: content => { uni.showModal({ title: '暂时无法删除', content, showCancel: false }) },
    })
    if (result === 'deleted') uni.showToast({ title: '档案已删除', icon: 'none' })
  } catch {
    // Clear stale selection even if the server succeeded but refreshing failed.
    profiles.value = []; selected.value = ''
    error.value = '未能确认删除结果，请刷新档案列表后重试。'
  } finally { deleting.value = false }
}
</script>

<template>
  <view class="page">
    <text v-if="loading">加载中...</text>
    <view v-else-if="error"><text>{{ error }}</text><button @click="load">重试</button></view>
    <view v-else-if="!profiles.length">暂无档案</view>
    <view v-for="p in profiles" :key="p.id" class="row">
      <text>{{ p.display_name }} · {{ p.relation }} {{ selected === p.id ? '（当前）' : '' }}</text>
      <button size="mini" :disabled="deleting" @click="choose(p.id)">切换</button>
      <button size="mini" :disabled="deleting" @click="edit(p.id)">编辑</button>
      <button size="mini" :disabled="deleting" @click="remove(p.id)">删除</button>
    </view>
    <button :disabled="deleting" @click="edit()">新增档案</button>
  </view>
</template>

<style scoped>
.page { padding: 36rpx; }
.row { padding: 20rpx 0; border-bottom: 1px solid #ddd; }
</style>
