<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { errorText, query, request, save, type Metric, type Page } from '../api'
import MetricDialog from '../components/MetricDialog.vue'
const rows = ref<Metric[]>([]), q = ref(''), status = ref(''), category = ref(''), page = ref(1), total = ref(0)
const loading = ref(false), busy = ref(false), error = ref(''), dialog = ref(false), editing = ref<Metric>()
async function load() {
  loading.value = true; error.value = ''
  try {
    const result = await request<Page<Metric>>(`/standard-metrics?${query({ q: q.value, status: status.value, category: category.value, page: page.value })}`)
    rows.value = result.items; total.value = result.total
  } catch (e) { rows.value = []; error.value = errorText(e) }
  finally { loading.value = false }
}
function search() { page.value = 1; void load() }
function edit(metric?: Metric) { editing.value = metric; dialog.value = true }
async function toggle(metric: Metric) {
  busy.value = true
  try { await save(`/standard-metrics/${metric.id}`, { status: metric.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE' }, 'PATCH'); await load() }
  catch (e) { ElMessage.error(errorText(e)) }
  finally { busy.value = false }
}
onMounted(load)
</script>
<template>
  <el-card>
    <h1>标准指标</h1>
    <div class="toolbar"><el-input v-model="q" placeholder="code / 名称" clearable @keyup.enter="search" /><el-select v-model="status" placeholder="全部状态" clearable><el-option label="ACTIVE" value="ACTIVE" /><el-option label="INACTIVE" value="INACTIVE" /></el-select><el-input v-model="category" placeholder="分类（精确）" clearable /><el-button @click="search">查询</el-button><el-button type="primary" @click="edit()">新增指标</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" /><el-button v-if="error" @click="load">重试</el-button>
    <el-table v-loading="loading" :data="rows" empty-text="暂无标准指标">
      <el-table-column prop="code" label="code" width="120" /><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="category" label="分类" /><el-table-column prop="status" label="状态" width="100" />
      <el-table-column prop="alias_count" label="别名数" width="80" /><el-table-column prop="formal_result_count" label="正式引用" width="100" /><el-table-column prop="pending_confirmation_count" label="待确认引用" width="100" /><el-table-column prop="updated_at" label="更新时间" min-width="180" />
      <el-table-column label="操作" width="260"><template #default="{ row }"><el-button link @click="$router.push(`/standard-metrics/${row.id}`)">详情 / 别名</el-button><el-button link @click="edit(row)">编辑</el-button><el-button link :disabled="busy" @click="toggle(row)">{{ row.status === 'ACTIVE' ? '停用' : '恢复' }}</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev, pager, next, total" @current-change="load" />
    <MetricDialog v-model="dialog" :metric="editing" @saved="load" />
  </el-card>
</template>
