<template>
  <el-card>
    <h1>标准指标与 OCR 管理</h1>
    <p>维护标准指标、别名，查看 OCR 名称覆盖问题与只读任务信息。</p>
    <p>别名用于未来首次确认的精确预关联，REVIEW 仍需人工确认；既往报告与已初始化工作区保持原数据。</p>
    <el-button @click="$router.push('/standard-metrics')">管理标准指标</el-button>
  </el-card>
</template>
