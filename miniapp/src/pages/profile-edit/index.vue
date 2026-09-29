<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { request, type Profile } from '../../api'

const id = ref('')
const name = ref('')
const relations = ['SELF', 'FATHER', 'MOTHER', 'SPOUSE', 'OTHER']
const relationLabels = ['本人', '父亲', '母亲', '配偶', '其他']
const relationIndex = ref(0)
const genders = ['', 'MALE', 'FEMALE', 'OTHER']
const genderLabels = ['未填写', '男', '女', '其他']
const genderIndex = ref(0)
const birthDate = ref('')
const error = ref('')
const saving = ref(false)
onLoad(async (params) => {
  if (!params?.id) return
  id.value = params.id
  try {
    const p = await request<Profile>(`/health-profiles/${id.value}`)
    name.value = p.display_name
    relationIndex.value = Math.max(0, relations.indexOf(p.relation))
    genderIndex.value = Math.max(0, genders.indexOf(p.gender || ''))
    birthDate.value = p.birth_date || ''
  } catch (e) { error.value = e instanceof Error ? e.message : '加载失败' }
})
async function save() {
  if (!name.value.trim()) { error.value = '请填写档案名称'; return }
  saving.value = true; error.value = ''
  try {
    const body = { display_name: name.value.trim(), relation: relations[relationIndex.value],
      gender: genders[genderIndex.value] || null, birth_date: birthDate.value || null }
    await request(id.value ? `/health-profiles/${id.value}` : '/health-profiles', id.value ? 'PUT' : 'POST', body)
    uni.navigateBack()
  } catch (e) { error.value = e instanceof Error ? e.message : '保存失败' }
  finally { saving.value = false }
}
</script>

<template>
  <view class="page">
    <text>档案名称</text><input v-model="name" placeholder="例如：本人、父亲" maxlength="80" />
    <text>关系</text><picker :range="relationLabels" :value="relationIndex" @change="relationIndex = Number($event.detail.value)"><view>{{ relationLabels[relationIndex] }}</view></picker>
    <text>性别（可选）</text><picker :range="genderLabels" :value="genderIndex" @change="genderIndex = Number($event.detail.value)"><view>{{ genderLabels[genderIndex] }}</view></picker>
    <text>生日（可选）</text><picker mode="date" :value="birthDate" @change="birthDate = String($event.detail.value)"><view>{{ birthDate || '请选择' }}</view></picker>
    <text v-if="error">{{ error }}</text>
    <button :disabled="saving" @click="save">保存</button>
  </view>
</template>

<style scoped>
.page { padding: 36rpx; display: flex; flex-direction: column; gap: 24rpx; }
input, picker { padding: 16rpx; border: 1px solid #ddd; }
</style>
