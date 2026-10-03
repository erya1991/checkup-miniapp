<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { errorText, query, request, save, type Metric, type Page } from '../api'
import { formatAdminTimeCell } from '../time'
import MetricDialog from '../components/MetricDialog.vue'
import PageHeader from '../components/PageHeader.vue'
import QueryError from '../components/QueryError.vue'
import StatusTag from '../components/StatusTag.vue'
const rows = ref<Metric[]>([]), q = ref(''), status = ref(''), category = ref(''), page = ref(1), total = ref(0)
const loading = ref(false), busy = ref(false), error = ref(''), dialog = ref(false), editing = ref<Metric>()
async function load() {
  loading.value = true; error.value = ''
  try {
    const result = await request<Page<Metric>>(`/standard-metrics?${query({ q: q.value, status: status.value, category: category.value, page: page.value })}`)
    rows.value = result.items; total.value = result.total
  } catch (e) { rows.value = []; total.value = 0; error.value = errorText(e) }
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
    <PageHeader title="标准指标" description="维护跨报告的指标身份。code 创建后只读，停用不影响已有正式历史。"><template #actions><el-button type="primary" @click="edit()">新增指标</el-button></template></PageHeader>
    <div class="toolbar"><el-input v-model="q" placeholder="搜索 code / 名称" clearable @keyup.enter="search" /><el-select v-model="status" placeholder="全部状态" clearable><el-option label="启用 · ACTIVE" value="ACTIVE" /><el-option label="停用 · INACTIVE" value="INACTIVE" /></el-select><el-input v-model="category" placeholder="分类（精确匹配）" clearable @keyup.enter="search" /><el-button :loading="loading" @click="search">查询</el-button></div>
    <QueryError :message="error" @retry="load" />
    <el-table v-if="!error" v-loading="loading" :data="rows" empty-text="暂无标准指标">
      <template #empty><el-empty :image-size="64" description="暂无符合条件的标准指标"><p>调整查询条件，或通过「新增指标」逐项维护。</p></el-empty></template>
      <el-table-column prop="code" label="code" width="120" show-overflow-tooltip /><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="category" label="分类" min-width="120" /><el-table-column prop="status" label="状态" width="150"><template #default="{ row }"><StatusTag :status="row.status" /></template></el-table-column>
      <el-table-column prop="alias_count" label="别名数" width="80" /><el-table-column prop="formal_result_count" label="正式引用" width="100" /><el-table-column prop="pending_confirmation_count" label="待确认引用" width="100" /><el-table-column prop="updated_at" label="更新时间" min-width="180" :formatter="formatAdminTimeCell" />
      <el-table-column label="操作" width="260" fixed="right"><template #default="{ row }"><el-button type="primary" link @click="$router.push(`/standard-metrics/${row.id}`)">详情 / 别名</el-button><el-button link @click="edit(row)">编辑</el-button><el-button link :type="row.status === 'ACTIVE' ? 'danger' : 'primary'" :disabled="busy" @click="toggle(row)">{{ row.status === 'ACTIVE' ? '停用' : '恢复' }}</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-if="!error && total > 0" v-model:current-page="page" :page-size="20" :total="total" layout="prev, pager, next, total" @current-change="load" />
    <MetricDialog v-model="dialog" :metric="editing" @saved="load" />
  </el-card>
</template>
