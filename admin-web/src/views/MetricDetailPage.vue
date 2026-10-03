<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { errorText, request, type Metric } from '../api'
import AliasTable from '../components/AliasTable.vue'
import MetricDialog from '../components/MetricDialog.vue'
import PageHeader from '../components/PageHeader.vue'
import QueryError from '../components/QueryError.vue'
import StatusTag from '../components/StatusTag.vue'
const route = useRoute(), metric = ref<Metric>(), loading = ref(false), error = ref(''), dialog = ref(false)
async function load() {
  loading.value = true; error.value = ''
  try { metric.value = await request<Metric>(`/standard-metrics/${encodeURIComponent(String(route.params.id))}`) }
  catch (e) { metric.value = undefined; error.value = errorText(e) }
  finally { loading.value = false }
}
watch(() => route.params.id, load, { immediate: true })
</script>
<template>
  <el-card v-loading="loading">
    <PageHeader title="标准指标详情" description="查看指标身份与引用摘要，维护名称、分类和所属别名。"><template #actions><el-button @click="$router.push('/standard-metrics')">返回列表</el-button><el-button v-if="metric" type="primary" @click="dialog = true">编辑指标</el-button></template></PageHeader>
    <QueryError :message="error" @retry="load" />
    <template v-if="metric">
      <el-descriptions :column="2" border><el-descriptions-item label="code">{{ metric.code }}</el-descriptions-item><el-descriptions-item label="名称">{{ metric.name }}</el-descriptions-item><el-descriptions-item label="分类">{{ metric.category || '未分类' }}</el-descriptions-item><el-descriptions-item label="状态"><StatusTag :status="metric.status" /></el-descriptions-item><el-descriptions-item label="正式引用">{{ metric.formal_result_count }}</el-descriptions-item><el-descriptions-item label="待确认引用">{{ metric.pending_confirmation_count }}</el-descriptions-item></el-descriptions>
      <div class="section-heading"><h2>指标别名</h2><p>别名目标创建后只读；已停用指标需先恢复，再新增别名。</p></div><AliasTable :metric="metric" @changed="load" />
      <MetricDialog v-model="dialog" :metric="metric" @saved="load" />
    </template>
  </el-card>
</template>
