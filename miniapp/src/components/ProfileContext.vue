<script setup lang="ts">
defineProps<{ name: string }>()
defineEmits<{ choose: [] }>()
</script>
<template><button class="profile-context text-action" @click="$emit('choose')"><text class="muted">当前健康档案</text><text class="section-title">{{ name }} ▾</text></button></template>
