<script setup lang="ts">
import AliasTable from '../components/AliasTable.vue'
import PageHeader from '../components/PageHeader.vue'
</script>
<template><el-card><PageHeader title="指标别名" description="维护常见名称与标准指标的精确关联，启用别名须满足唯一性和名称空间校验。" /><AliasTable /></el-card></template>
