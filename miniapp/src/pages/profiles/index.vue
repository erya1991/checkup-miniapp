<script setup lang="ts">
import { ref } from 'vue'
import { onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { deleteWithConfirmation, profileContext, type DeletionImpact, type ProfileContext } from '../../profile-deletion'
import { requestGuard } from '../../profile-metrics'
import { navigate, tabPaths } from '../../navigation'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import StatusTag from '../../components/StatusTag.vue'
const profiles = ref<Profile[]>([]), selected = ref(''), loading = ref(true), error = ref('')
const deleting = ref(false), choosing = ref(false), choosingMore = ref(false)
const choosingId = ref('')
let visible = false
const guard = requestGuard()
const relations: Record<string, string> = { SELF: '本人', FATHER: '父亲', MOTHER: '母亲', SPOUSE: '配偶', OTHER: '其他家人' }
async function context() {
  const me = await ensureLogin()
  const rows = await request<Profile[]>('/health-profiles')
  return profileContext(rows, me.default_health_profile_id)
}
function applyContext(next: ProfileContext) {
  profiles.value = next.profiles; selected.value = next.selected
}
async function load() {
  if (deleting.value || choosing.value) return
  const run = guard.next()
  loading.value = true; error.value = ''; profiles.value = []; selected.value = ''
  try {
    const next = await context()
    if (guard.current(run)) applyContext(next)
  } catch (e) { if (guard.current(run)) error.value = userError(e, '健康档案加载失败，请重试。') }
  finally { if (guard.current(run)) loading.value = false }
}
onShow(() => { visible = true; load() })
onHide(() => { visible = false; guard.invalidate() })
onUnload(() => guard.invalidate())
function edit(id?: string) { navigate(`/pages/profile-edit/index${id ? '?id=' + encodeURIComponent(id) : ''}`) }
async function choose(id: string) {
  if (deleting.value || choosing.value) return
  const run = guard.next()
  choosing.value = true; choosingId.value = id; error.value = ''
  try {
    await request('/me/default-health-profile', 'PUT', { health_profile_id: id })
    if (!guard.current(run)) return
    selected.value = id
    uni.navigateBack({ fail: () => navigate(tabPaths.home) })
  } catch (e) { if (guard.current(run)) error.value = userError(e, '档案切换失败，请重试。') }
  finally {
    choosing.value = false; choosingId.value = ''
    if (!guard.current(run) && visible) load()
  }
}
async function more(id: string) {
  if (deleting.value || choosing.value || choosingMore.value) return
  choosingMore.value = true
  try {
    const choice = await uni.showActionSheet({ itemList: ['永久删除档案'], itemColor: '#b42318' })
    if (choice.tapIndex === 0) await remove(id)
  } catch { /* Native action sheet cancellation needs no error feedback. */ }
  finally { choosingMore.value = false }
}
async function remove(id: string) {
  if (deleting.value) return
  const run = guard.next()
  deleting.value = true; error.value = ''
  try {
    const result = await deleteWithConfirmation(id, {
      impact: () => request<DeletionImpact>(`/health-profiles/${encodeURIComponent(id)}/deletion-impact`),
      confirm: async content => guard.current(run) && !!(await uni.showModal({ title: '永久删除档案', content, confirmText: '永久删除', confirmColor: '#b42318' })).confirm && guard.current(run),
      remove: () => request(`/health-profiles/${encodeURIComponent(id)}`, 'DELETE'),
      reload: context,
      apply: next => { if (guard.current(run)) applyContext(next) },
      notify: content => { if (guard.current(run)) uni.showModal({ title: '暂时无法删除', content, showCancel: false }) },
    })
    if (guard.current(run) && result === 'deleted') uni.showToast({ title: '档案已删除', icon: 'none' })
  } catch {
    if (guard.current(run)) {
      // A lost DELETE response cannot be retried until server facts are refreshed.
      profiles.value = []; selected.value = ''
      error.value = '未能确认删除结果，请刷新档案列表后重试。'
    }
  } finally {
    deleting.value = false
    if (!guard.current(run) && visible) load()
  }
}
</script>
<template>
  <PageContainer>
    <text class="title">健康档案</text>
    <text class="muted">选择正在查看的家人，报告、指标和关注状态会随档案切换。</text>
    <UiState v-if="loading" type="loading" title="正在加载健康档案" />
    <UiState v-if="error" type="error" title="暂时无法完成操作" :description="error" action="刷新档案列表" @action="load" />
    <UiState v-if="!loading && !error && !profiles.length" type="empty" title="还没有健康档案" description="先创建本人档案，再开始整理检验报告。" action="创建本人档案" @action="edit()" />
    <view v-for="p in profiles" :key="p.id" class="card">
      <view class="section-heading">
        <text class="section-title">{{ p.display_name }}</text>
        <StatusTag v-if="selected === p.id" tone="success" label="当前档案" />
      </view>
      <text class="muted">{{ relations[p.relation] || '家人' }}</text>
      <view class="actions">
        <button v-if="selected !== p.id" class="secondary" :disabled="deleting || choosing" :loading="choosingId === p.id" @click="choose(p.id)">切换到此档案</button>
        <button class="text-action" :disabled="deleting || choosing" @click="edit(p.id)">编辑</button>
        <button class="text-action" :disabled="deleting || choosing || choosingMore" @click="more(p.id)">更多</button>
      </view>
    </view>
    <button v-if="!loading && profiles.length" class="primary" :disabled="deleting || choosing" @click="edit()">新增健康档案</button>
    <text v-if="profiles.length" class="muted">每个档案独立保存报告及关注。永久删除可在更多操作中进行，会先显示影响范围。</text>
  </PageContainer>
</template>
