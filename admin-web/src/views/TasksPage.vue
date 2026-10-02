<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorText, query, request, type Page, type Task } from '../api'
import { formatAdminTimeCell } from '../time'
const rows = ref<Task[]>([]), status = ref(''), version = ref(''), page = ref(1), total = ref(0), loading = ref(false), error = ref('')
async function load() {
  loading.value = true; error.value = ''
  try {
    const data = await request<Page<Task>>(`/ocr-tasks?${query({ status: status.value, pipeline_version: version.value, page: page.value })}`)
    rows.value = data.items; total.value = data.total
  } catch (e) { rows.value = []; error.value = errorText(e) }
  finally { loading.value = false }
}
function search() { page.value = 1; void load() }
onMounted(load)
</script>
<template>
  <el-card>
    <h1>OCR 任务（只读）</h1>
    <div class="toolbar"><el-select v-model="status" clearable placeholder="全部状态"><el-option v-for="s in ['QUEUED', 'PROCESSING', 'SUCCEEDED', 'FAILED']" :key="s" :label="s" :value="s" /></el-select><el-input v-model="version" clearable placeholder="Pipeline Version（精确）" @keyup.enter="search" /><el-button @click="search">查询</el-button></div>
    <el-alert v-if="error" :title="error" type="error" :closable="false" /><el-button v-if="error" @click="load">重试</el-button>
    <el-table v-loading="loading" :data="rows" empty-text="暂无 OCR 任务">
      <el-table-column prop="id" label="任务 id" width="260" /><el-table-column prop="ingestion_id" label="导入 id" width="260" /><el-table-column prop="run_no" label="run" width="60" /><el-table-column prop="status" label="状态" width="120" /><el-table-column prop="pipeline_version" label="Pipeline Version" width="260" /><el-table-column prop="attempt_count" label="attempt" width="90" />
      <el-table-column label="数量摘要" width="180"><template #default="{ row }">总数 {{ row.result_summary.total_count ?? '—' }} / AUTO {{ row.result_summary.auto_count ?? '—' }} / REVIEW {{ row.result_summary.review_count ?? '—' }}</template></el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="220" :formatter="formatAdminTimeCell" /><el-table-column prop="started_at" label="开始时间" width="220" :formatter="formatAdminTimeCell" /><el-table-column prop="finished_at" label="完成时间" width="220" :formatter="formatAdminTimeCell" /><el-table-column prop="last_error_code" label="错误码" width="180" />
    </el-table>
    <el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev, pager, next, total" @current-change="load" />
  </el-card>
</template>
