<script setup lang="ts">
withDefaults(defineProps<{ label: string; tone?: 'neutral' | 'warning' | 'success' | 'abnormal' | 'danger' }>(), { tone: 'neutral' })
</script>
<template><text class="tag" :class="'tag-' + tone">{{ label }}</text></template>
