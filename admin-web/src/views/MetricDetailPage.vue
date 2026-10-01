<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { errorText, request, type Metric } from '../api'
import AliasTable from '../components/AliasTable.vue'
import MetricDialog from '../components/MetricDialog.vue'
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
    <el-button @click="$router.push('/standard-metrics')">返回列表</el-button><h1>标准指标详情</h1>
    <el-alert v-if="error" :title="error" type="error" :closable="false" /><el-button v-if="error" @click="load">重试</el-button>
    <template v-if="metric">
      <el-descriptions :column="3" border><el-descriptions-item label="code">{{ metric.code }}</el-descriptions-item><el-descriptions-item label="名称">{{ metric.name }}</el-descriptions-item><el-descriptions-item label="分类">{{ metric.category || '未分类' }}</el-descriptions-item><el-descriptions-item label="状态">{{ metric.status }}</el-descriptions-item><el-descriptions-item label="正式引用">{{ metric.formal_result_count }}</el-descriptions-item><el-descriptions-item label="待确认引用">{{ metric.pending_confirmation_count }}</el-descriptions-item></el-descriptions>
      <el-button style="margin-top: 16px" @click="dialog = true">编辑名称 / 分类</el-button>
      <h2>指标别名</h2><AliasTable :metric="metric" @changed="load" />
      <MetricDialog v-model="dialog" :metric="metric" @saved="load" />
    </template>
  </el-card>
</template>
