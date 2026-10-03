<script setup lang="ts">
import PageHeader from '../components/PageHeader.vue'
const modules = [
  { path: '/standard-metrics', title: '标准指标', description: '维护指标名称、分类与启用状态，查看正式和待确认引用。' },
  { path: '/metric-aliases', title: '指标别名', description: '维护常见名称与 OCR 变体的精确关联。' },
  { path: '/ocr-metric-issues', title: 'OCR 指标问题', description: '查看尚未覆盖的名称、缺失或停用的指标 code。' },
  { path: '/ocr-tasks', title: 'OCR 任务', description: '只读查看任务状态、Pipeline Version 和识别数量摘要。' },
]
</script>
<template>
  <el-card>
    <PageHeader title="管理首页" description="维护标准指标和别名，查看 OCR 名称覆盖问题与任务信息。" />
    <div class="module-grid"><button v-for="module in modules" :key="module.path" type="button" class="module-link" @click="$router.push(module.path)"><strong>{{ module.title }} →</strong><span>{{ module.description }}</span></button></div>
    <p class="home-note">别名用于未来首次确认的精确预关联，REVIEW 仍需人工确认。既往报告与已初始化工作区保持原数据。</p>
  </el-card>
</template>
