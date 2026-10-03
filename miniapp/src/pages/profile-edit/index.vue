<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { request, type Profile } from '../../api'
import { requestGuard } from '../../profile-metrics'
import { navigate, tabPaths } from '../../navigation'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
const id = ref(''), name = ref(''), nameError = ref('')
const relations = ['SELF', 'FATHER', 'MOTHER', 'SPOUSE', 'OTHER']
const relationLabels = ['本人', '父亲', '母亲', '配偶', '其他']
const relationIndex = ref(0)
const genders = ['', 'MALE', 'FEMALE', 'OTHER']
const genderLabels = ['未填写', '男', '女', '其他']
const genderIndex = ref(0), birthDate = ref(''), error = ref('')
const saving = ref(false), loading = ref(false), loaded = ref(true)
const guard = requestGuard()
onLoad(params => { if (params?.id) { id.value = params.id; load() } })
onUnload(() => guard.invalidate())
async function load() {
  if (!id.value || loading.value) return
  const run = guard.next()
  loading.value = true; loaded.value = false; error.value = ''
  try {
    const p = await request<Profile>(`/health-profiles/${encodeURIComponent(id.value)}`)
    if (!guard.current(run)) return
    name.value = p.display_name
    relationIndex.value = Math.max(0, relations.indexOf(p.relation))
    genderIndex.value = Math.max(0, genders.indexOf(p.gender || ''))
    birthDate.value = p.birth_date || ''
    loaded.value = true
  } catch (e) { if (guard.current(run)) error.value = userError(e, '档案加载失败，请重试。') }
  finally { if (guard.current(run)) loading.value = false }
}
async function save() {
  if (saving.value || loading.value || !loaded.value) return
  if (!name.value.trim()) { nameError.value = '请填写档案名称，例如本人或父亲'; error.value = '请检查档案名称后再保存。'; return }
  const run = guard.next()
  saving.value = true; error.value = ''; nameError.value = ''
  try {
    const body = { display_name: name.value.trim(), relation: relations[relationIndex.value],
      gender: genders[genderIndex.value] || null, birth_date: birthDate.value || null }
    await request(id.value ? `/health-profiles/${encodeURIComponent(id.value)}` : '/health-profiles', id.value ? 'PUT' : 'POST', body)
    if (!guard.current(run)) return
    uni.showToast({ title: '档案已保存', icon: 'success' })
    uni.navigateBack({ fail: () => navigate(tabPaths.home) })
  } catch (e) { if (guard.current(run)) error.value = userError(e, '保存失败，请检查网络后重试。') }
  finally { if (guard.current(run)) saving.value = false }
}
</script>
<template>
  <PageContainer>
    <text class="title">{{ id ? '编辑健康档案' : '创建健康档案' }}</text>
    <text class="muted">名称用于区分家人，性别和生日可以暂时不填写。</text>
    <UiState v-if="loading" type="loading" title="正在加载档案" />
    <UiState v-if="error && !loaded" type="error" title="暂时无法加载档案" :description="error" action="重新加载" @action="load" />
    <template v-if="loaded && !loading">
      <text v-if="error" class="error">{{ error }}</text>
      <view class="card">
        <view class="form-field">
          <text class="label">档案名称 · 必填</text>
          <input v-model="name" class="field" :class="{ 'invalid-field': nameError }" :disabled="saving" placeholder="例如：本人、父亲" maxlength="80" @input="nameError = ''" />
          <text v-if="nameError" class="error">{{ nameError }}</text>
        </view>
        <view class="form-field">
          <text class="label">与我的关系</text>
          <picker :range="relationLabels" :value="relationIndex" :disabled="saving" @change="relationIndex = Number($event.detail.value)"><view class="field">{{ relationLabels[relationIndex] }} ▾</view></picker>
        </view>
        <view class="form-field">
          <text class="label">性别 · 可选</text>
          <picker :range="genderLabels" :value="genderIndex" :disabled="saving" @change="genderIndex = Number($event.detail.value)"><view class="field">{{ genderLabels[genderIndex] }} ▾</view></picker>
        </view>
        <view class="form-field">
          <text class="label">生日 · 可选</text>
          <picker mode="date" :value="birthDate" :disabled="saving" @change="birthDate = String($event.detail.value)"><view class="field">{{ birthDate || '请选择生日' }} ▾</view></picker>
          <button v-if="birthDate" class="text-action" :disabled="saving" @click="birthDate = ''">清除生日</button>
        </view>
      </view>
      <button class="primary" :disabled="saving" :loading="saving" @click="save">保存健康档案</button>
    </template>
  </PageContainer>
</template>
<style scoped>
.form-field { display: flex; flex-direction: column; gap: 12rpx; }
.invalid-field { border-color: var(--danger); }
</style>
