<script setup lang="ts">
import { onShow } from '@dcloudio/uni-app'
import { openReports } from '../../navigation'
// Compatibility entry: the Report Tab owns the current profile and both views.
onShow(() => openReports('metrics'))
</script>
<template><view /></template>
