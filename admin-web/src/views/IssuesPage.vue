<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { errorText, query, request, save, type Issue, type Page } from '../api'
import { formatAdminTimeCell } from '../time'
import AliasDialog from '../components/AliasDialog.vue'
import MetricDialog from '../components/MetricDialog.vue'
import PageHeader from '../components/PageHeader.vue'
import QueryError from '../components/QueryError.vue'
const kind = ref('UNMATCHED_NAME'), rows = ref<Issue[]>([]), page = ref(1), total = ref(0)
const loading = ref(false), busy = ref(false), error = ref(''), aliasDialog = ref(false), metricDialog = ref(false)
const aliasSeed = ref(''), metricSeed = ref<{ code?: string; name?: string }>({})
async function load() {
  loading.value = true; error.value = ''
  try {
    const data = await request<Page<Issue>>(`/ocr-metric-issues?${query({ issue_type: kind.value, page: page.value })}`)
    rows.value = data.items; total.value = data.total
  } catch (e) { rows.value = []; total.value = 0; error.value = errorText(e) }
  finally { loading.value = false }
}
function tab() { page.value = 1; void load() }
async function act(row: Issue) {
  if (row.issue_type === 'UNMATCHED_NAME') { aliasSeed.value = row.representative_name || ''; aliasDialog.value = true }
  else if (row.issue_type === 'PRODUCT_METRIC_MISSING') { metricSeed.value = { code: row.ocr_code, name: row.ocr_standard_name }; metricDialog.value = true }
  else {
    busy.value = true
    try { await save(`/standard-metrics/${row.standard_metric_id}`, { status: 'ACTIVE' }, 'PATCH'); await load() }
    catch (e) { ElMessage.error(errorText(e)) }
    finally { busy.value = false }
  }
}
onMounted(load)
</script>
<template>
  <el-card>
    <PageHeader title="OCR 指标问题" description="每份报告仅统计最新成功识别。维护主数据后，列表按当前覆盖情况更新，历史识别快照保持原样。"><template #actions><el-button :loading="loading" @click="load">刷新列表</el-button></template></PageHeader>
    <el-tabs v-model="kind" @tab-change="tab"><el-tab-pane label="未匹配名称" name="UNMATCHED_NAME" /><el-tab-pane label="产品主数据缺失 code" name="PRODUCT_METRIC_MISSING" /><el-tab-pane label="已停用 code" name="PRODUCT_METRIC_INACTIVE" /></el-tabs>
    <QueryError :message="error" @retry="load" />
    <el-table v-if="!error" v-loading="loading" :data="rows" empty-text="暂无待处理指标问题">
      <template #empty><el-empty :image-size="64" description="当前分类没有待处理指标问题"><p>可查看其它分类，或识别新测试报告后刷新列表。</p></el-empty></template>
      <el-table-column label="名称 / code" min-width="180"><template #default="{ row }">{{ row.representative_name || row.ocr_code }}</template></el-table-column>
      <el-table-column label="归一化 / OCR 标准名称" min-width="180"><template #default="{ row }">{{ row.normalized_name || row.ocr_standard_name || '未记录' }}</template></el-table-column>
      <el-table-column prop="occurrence_count" label="出现次数" width="100" /><el-table-column prop="ingestion_count" label="报告次数" width="100" /><el-table-column prop="latest_seen_at" label="最近出现" min-width="180" :formatter="formatAdminTimeCell" />
      <el-table-column label="名称样例" min-width="180"><template #default="{ row }">{{ row.sample_names?.join(' / ') || '—' }}</template></el-table-column>
      <el-table-column label="操作" width="180" fixed="right"><template #default="{ row }"><el-button type="primary" link :disabled="busy" @click="act(row)">{{ row.issue_type === 'UNMATCHED_NAME' ? '创建别名' : row.issue_type === 'PRODUCT_METRIC_MISSING' ? '创建标准指标' : '恢复标准指标' }}</el-button></template></el-table-column>
    </el-table>
    <el-pagination v-if="!error && total > 0" v-model:current-page="page" :page-size="20" :total="total" layout="prev, pager, next, total" @current-change="load" />
    <AliasDialog v-model="aliasDialog" :seed="aliasSeed" @saved="load" /><MetricDialog v-model="metricDialog" :seed="metricSeed" @saved="load" />
  </el-card>
</template>
