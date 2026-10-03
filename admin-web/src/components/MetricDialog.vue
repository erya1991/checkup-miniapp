<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { errorText, save, type Metric } from '../api'
const props = defineProps<{ modelValue: boolean; metric?: Metric; seed?: { code?: string; name?: string } }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()
const form = reactive({ code: '', name: '', category: '' }), loading = ref(false), error = ref('')
watch(() => props.modelValue, open => {
  if (open) {
    form.code = props.metric?.code || props.seed?.code || ''
    form.name = props.metric?.name || props.seed?.name || ''
    form.category = props.metric?.category || ''; error.value = ''
  }
})
async function submit() {
  if (loading.value || !form.code.trim() || !form.name.trim()) return
  loading.value = true; error.value = ''
  try {
    const value = { name: form.name, category: form.category || null }
    if (props.metric) await save(`/standard-metrics/${props.metric.id}`, value, 'PATCH')
    else await save('/standard-metrics', { ...value, code: form.code })
    emit('update:modelValue', false); emit('saved')
  } catch (e) { error.value = errorText(e) }
  finally { loading.value = false }
}
</script>
<template>
  <el-dialog :model-value="modelValue" :title="metric ? '编辑标准指标' : '新增标准指标'" class="admin-dialog" width="min(520px, calc(100vw - 32px))" :close-on-click-modal="false" :close-on-press-escape="!loading" :show-close="!loading" @update:model-value="emit('update:modelValue', $event)">
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="code" required><el-input v-model="form.code" :disabled="!!metric" placeholder="稳定指标标识，创建后只读" maxlength="64" /></el-form-item>
      <el-form-item label="名称" required><el-input v-model="form.name" placeholder="标准指标名称" maxlength="256" /></el-form-item>
      <el-form-item label="分类（可选）"><el-input v-model="form.category" placeholder="例如：肝功能" maxlength="80" /></el-form-item>
    </el-form>
    <p class="form-note">code 创建后只读，名称修改不覆盖既往正式报告的项目名称。</p>
    <template #footer><el-button @click="emit('update:modelValue', false)" :disabled="loading">取消</el-button><el-button type="primary" :loading="loading" :disabled="!form.code.trim() || !form.name.trim()" @click="submit">保存</el-button></template>
  </el-dialog>
</template>
