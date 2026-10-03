<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { errorText, request, save, query, type Alias, type Metric, type Page } from '../api'
const props = defineProps<{ modelValue: boolean; alias?: Alias; metric?: Metric; seed?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; saved: [] }>()
const form = reactive({ standard_metric_id: '', alias: '', alias_type: 'SYNONYM' })
const options = ref<Metric[]>([]), loading = ref(false), searching = ref(false), error = ref('')
const types = ['SYNONYM', 'ABBREVIATION', 'OCR_VARIANT', 'HOSPITAL_NAME']
async function search(q = '') {
  searching.value = true
  try { options.value = (await request<Page<Metric>>(`/standard-metrics?${query({ q, status: 'ACTIVE', page_size: 100 })}`)).items }
  catch (e) { error.value = errorText(e) }
  finally { searching.value = false }
}
watch(() => props.modelValue, open => {
  if (open) {
    form.standard_metric_id = props.alias?.standard_metric_id || props.metric?.id || ''
    form.alias = props.alias?.alias || props.seed || ''
    form.alias_type = props.alias?.alias_type || 'SYNONYM'; error.value = ''
    if (props.metric) options.value = [props.metric]
    else if (props.alias) options.value = [{ id: props.alias.standard_metric_id, code: props.alias.metric_code, name: props.alias.metric_name } as Metric]
    else void search()
  }
})
async function submit() {
  if (loading.value || !form.standard_metric_id || !form.alias.trim()) return
  loading.value = true; error.value = ''
  try {
    const value = { alias: form.alias, alias_type: form.alias_type }
    if (props.alias) await save(`/metric-aliases/${props.alias.id}`, value, 'PATCH')
    else await save('/metric-aliases', { ...value, standard_metric_id: form.standard_metric_id })
    emit('update:modelValue', false); emit('saved')
  } catch (e) { error.value = errorText(e) }
  finally { loading.value = false }
}
</script>
<template>
  <el-dialog :model-value="modelValue" :title="alias ? '编辑别名' : '新增别名'" class="admin-dialog" width="min(560px, calc(100vw - 32px))" :close-on-click-modal="false" :close-on-press-escape="!loading" :show-close="!loading" @update:model-value="emit('update:modelValue', $event)">
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="目标标准指标" required><el-select v-model="form.standard_metric_id" filterable remote :remote-method="search" :loading="searching" :disabled="!!alias || !!metric" placeholder="输入 code / 名称搜索"><el-option v-for="m in options" :key="m.id" :label="`${m.name} (${m.code})`" :value="m.id" /></el-select></el-form-item>
      <el-form-item label="别名" required><el-input v-model="form.alias" placeholder="报告上的常见名称或 OCR 变体" maxlength="256" /></el-form-item>
      <el-form-item label="类型" required><el-select v-model="form.alias_type"><el-option v-for="t in types" :key="t" :label="t" :value="t" /></el-select></el-form-item>
    </el-form>
    <p class="form-note">目标创建后只读；别名只影响未来首次确认与搜索，REVIEW 仍需人工处理。</p>
    <template #footer><el-button @click="emit('update:modelValue', false)" :disabled="loading">取消</el-button><el-button type="primary" :loading="loading" :disabled="!form.standard_metric_id || !form.alias.trim()" @click="submit">保存</el-button></template>
  </el-dialog>
</template>
