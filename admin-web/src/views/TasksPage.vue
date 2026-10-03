<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorText, query, request, type Page, type Task } from '../api'
import { formatAdminTimeCell } from '../time'
import { adminStatus } from '../presentation'
import PageHeader from '../components/PageHeader.vue'
import QueryError from '../components/QueryError.vue'
import StatusTag from '../components/StatusTag.vue'
const rows = ref<Task[]>([]), status = ref(''), version = ref(''), page = ref(1), total = ref(0), loading = ref(false), error = ref('')
async function load() {
  loading.value = true; error.value = ''
  try {
    const data = await request<Page<Task>>(`/ocr-tasks?${query({ status: status.value, pipeline_version: version.value, page: page.value })}`)
    rows.value = data.items; total.value = data.total
  } catch (e) { rows.value = []; total.value = 0; error.value = errorText(e) }
  finally { loading.value = false }
}
function search() { page.value = 1; void load() }
onMounted(load)
</script>
<template>
  <el-card>
    <PageHeader title="OCR 任务" description="只读查看任务状态与机器初始识别摘要，时间统一为北京时间。AUTO / REVIEW 数量不代表当前人工确认进度。" />
    <div class="toolbar"><el-select v-model="status" clearable placeholder="全部状态"><el-option v-for="s in ['QUEUED', 'PROCESSING', 'SUCCEEDED', 'FAILED']" :key="s" :label="adminStatus(s).label" :value="s" /></el-select><el-input v-model="version" clearable placeholder="Pipeline Version（精确匹配）" @keyup.enter="search" /><el-button :loading="loading" @click="search">查询</el-button></div>
    <QueryError :message="error" @retry="load" />
    <el-table v-if="!error" v-loading="loading" :data="rows" empty-text="暂无 OCR 任务">
      <template #empty><el-empty :image-size="64" description="暂无符合条件的 OCR 任务"><p>调整状态或 Pipeline Version 条件后重新查询。</p></el-empty></template>
      <el-table-column prop="status" label="状态" width="180" fixed="left"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
      <el-table-column prop="id" label="任务 id" width="260" show-overflow-tooltip /><el-table-column prop="ingestion_id" label="导入 id" width="260" show-overflow-tooltip /><el-table-column prop="run_no" label="run" width="60" /><el-table-column prop="pipeline_version" label="Pipeline Version" width="260" show-overflow-tooltip /><el-table-column prop="attempt_count" label="attempt" width="90" />
      <el-table-column label="机器初始数量" width="180"><template #default="{ row }"><div class="task-summary"><span>总数 {{ row.result_summary.total_count ?? '—' }}</span><span>AUTO {{ row.result_summary.auto_count ?? '—' }} / REVIEW {{ row.result_summary.review_count ?? '—' }}</span></div></template></el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="220" :formatter="formatAdminTimeCell" /><el-table-column prop="started_at" label="开始时间" width="220" :formatter="formatAdminTimeCell" /><el-table-column prop="finished_at" label="完成时间" width="220" :formatter="formatAdminTimeCell" /><el-table-column prop="last_error_code" label="错误码" width="180" />
    </el-table>
    <el-pagination v-if="!error && total > 0" v-model:current-page="page" :page-size="20" :total="total" layout="prev, pager, next, total" @current-change="load" />
  </el-card>
</template>
