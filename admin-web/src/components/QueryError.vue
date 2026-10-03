<script setup lang="ts">
defineProps<{ message: string }>()
defineEmits<{ retry: [] }>()
</script>
<template>
  <div v-if="message" class="query-error" role="alert">
    <el-alert :title="message" type="error" show-icon :closable="false" />
    <el-button @click="$emit('retry')">重新加载</el-button>
  </div>
</template>
