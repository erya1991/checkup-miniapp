<script setup lang="ts">
withDefaults(defineProps<{ type: 'loading' | 'empty' | 'error'; title: string; description?: string; action?: string }>(), { description: '', action: '' })
defineEmits<{ action: [] }>()
</script>
<template>
  <view class="ui-state" :class="{ 'state-error': type === 'error' }" role="status">
    <text class="section-title">{{ title }}</text>
    <text v-if="description" class="muted">{{ description }}</text>
    <button v-if="action && type !== 'loading'" class="secondary" @click="$emit('action')">{{ action }}</button>
  </view>
</template>
