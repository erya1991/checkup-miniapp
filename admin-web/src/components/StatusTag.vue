<script setup lang="ts">
import { computed } from 'vue'
import { adminStatus } from '../presentation'
const props = defineProps<{ status: string }>()
const presentation = computed(() => adminStatus(props.status))
</script>
<template><el-tag :type="presentation.type" effect="light" size="small">{{ presentation.label }}</el-tag></template>
