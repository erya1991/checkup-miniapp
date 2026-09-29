<script setup lang="ts">
import { ref } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'

const profiles = ref<Profile[]>([])
const selected = ref('')
const loading = ref(true)
const error = ref('')
async function load() {
  loading.value = true; error.value = ''
  try {
    const me = await ensureLogin()
    profiles.value = await request<Profile[]>('/health-profiles')
    selected.value = me.default_health_profile_id || ''
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
  const result = await uni.showModal({ title: '删除档案', content: '有导入任务的档案不能直接删除。确认删除？' })
  if (!result.confirm) return
  try { await request(`/health-profiles/${id}`, 'DELETE'); await load() }
  catch (e) { uni.showToast({ title: e instanceof Error ? e.message : '删除失败', icon: 'none' }) }
}
</script>

<template>
  <view class="page">
    <text v-if="loading">加载中...</text>
    <view v-else-if="error"><text>{{ error }}</text><button @click="load">重试</button></view>
    <view v-else-if="!profiles.length">暂无档案</view>
    <view v-for="p in profiles" :key="p.id" class="row">
      <text>{{ p.display_name }} · {{ p.relation }} {{ selected === p.id ? '（当前）' : '' }}</text>
      <button size="mini" @click="choose(p.id)">切换</button>
      <button size="mini" @click="edit(p.id)">编辑</button>
      <button size="mini" @click="remove(p.id)">删除</button>
    </view>
    <button @click="edit()">新增档案</button>
  </view>
</template>

<style scoped>
.page { padding: 36rpx; }
.row { padding: 20rpx 0; border-bottom: 1px solid #ddd; }
</style>
