<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { onShow } from '@dcloudio/uni-app'
import { fontScale } from '../ui'
const scale = ref(1)
function refreshFont() { try { scale.value = fontScale(uni.getAppBaseInfo()) } catch { scale.value = 1 } }
onShow(refreshFont)
onMounted(refreshFont)
</script>
<template><view class="page" :style="{ '--font-scale': scale }"><slot /></view></template>
