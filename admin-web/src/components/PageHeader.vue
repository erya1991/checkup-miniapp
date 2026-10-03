<script setup lang="ts">
defineProps<{ title: string; description: string }>()
</script>
<template>
  <div class="page-header">
    <div class="page-heading"><h1>{{ title }}</h1><p>{{ description }}</p></div>
    <div v-if="$slots.actions" class="page-actions"><slot name="actions" /></div>
  </div>
</template>
