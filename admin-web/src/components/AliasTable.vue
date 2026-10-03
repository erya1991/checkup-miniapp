<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { errorText, query, request, save, type Alias, type Metric, type Page } from '../api'
import AliasDialog from './AliasDialog.vue'
import QueryError from './QueryError.vue'
import StatusTag from './StatusTag.vue'
const props = defineProps<{ metric?: Metric }>()
const emit = defineEmits<{ changed: [] }>()
const rows = ref<Alias[]>([]), q = ref(''), status = ref(''), page = ref(1), total = ref(0)
const loading = ref(false), busy = ref(false), error = ref(''), dialog = ref(false), editing = ref<Alias>()
async function load() {
  loading.value = true; error.value = ''
  try {
    const data = await request<Page<Alias>>(`/metric-aliases?${query({ q: q.value, status: status.value, standard_metric_id: props.metric?.id, page: page.value })}`)
    rows.value = data.items; total.value = data.total
  } catch (e) { rows.value = []; total.value = 0; error.value = errorText(e) }
  finally { loading.value = false }
}
function edit(row?: Alias) { editing.value = row; dialog.value = true }
function search() { page.value = 1; void load() }
async function changed() { await load(); emit('changed') }
async function toggle(row: Alias) {
  busy.value = true
  try { await save(`/metric-aliases/${row.id}`, { status: row.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE' }, 'PATCH'); await changed() }
  catch (e) { ElMessage.error(errorText(e)) }
  finally { busy.value = false }
}
watch(() => props.metric?.id, search, { immediate: true })
</script>
<template>
  <div class="toolbar"><el-input v-model="q" placeholder="搜索别名" clearable @keyup.enter="search" /><el-select v-model="status" clearable placeholder="全部状态"><el-option label="启用 · ACTIVE" value="ACTIVE" /><el-option label="停用 · INACTIVE" value="INACTIVE" /></el-select><el-button :loading="loading" @click="search">查询</el-button><el-button type="primary" :disabled="metric && metric.status !== 'ACTIVE'" @click="edit()">新增别名</el-button></div>
  <QueryError :message="error" @retry="load" />
  <el-table v-if="!error" v-loading="loading" :data="rows" empty-text="暂无别名">
    <template #empty><el-empty :image-size="64" description="暂无符合条件的指标别名"><p>调整查询条件，或为启用指标新增别名。</p></el-empty></template>
    <el-table-column prop="alias" label="原始别名" min-width="180" /><el-table-column prop="normalized_alias" label="归一化名称" min-width="160" /><el-table-column prop="metric_code" label="目标 code" width="120" /><el-table-column prop="metric_name" label="目标名称" min-width="160" /><el-table-column prop="alias_type" label="类型" width="160" /><el-table-column prop="status" label="状态" width="150"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
    <el-table-column label="操作" width="180" fixed="right"><template #default="{ row }"><el-button link @click="edit(row)">编辑</el-button><el-button link :type="row.status === 'ACTIVE' ? 'danger' : 'primary'" :disabled="busy" @click="toggle(row)">{{ row.status === 'ACTIVE' ? '停用' : '恢复' }}</el-button></template></el-table-column>
  </el-table>
  <el-pagination v-if="!error && total > 0" v-model:current-page="page" :page-size="20" :total="total" layout="prev, pager, next, total" @current-change="load" />
  <AliasDialog v-model="dialog" :alias="editing" :metric="metric" @saved="changed" />
</template>
