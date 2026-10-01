<script setup lang="ts">
import { computed } from 'vue'
import { chartGeometry, type TrendPoint } from '../profile-metrics'
const props = defineProps<{ points: TrendPoint[]; selectedId: string }>()
const emit = defineEmits<{ select: [point: TrendPoint] }>()
const chart = computed(() => chartGeometry(props.points))
</script>
<template>
  <view class="chart">
    <text class="scale">数值范围：{{ chart.min }} ～ {{ chart.max }}</text>
    <scroll-view scroll-x class="scroll">
      <view class="plot" :style="{ width: chart.width + 'px' }">
        <view v-for="line in chart.lines" :key="line.id" class="line"
          :style="{ left: line.x + 'px', top: line.y + 'px', width: line.width + 'px', transform: 'rotate(' + line.angle + 'deg)' }" />
        <button v-for="dot in chart.dots" :key="dot.point.lab_result_id" class="point"
          :class="{ selected: selectedId === dot.point.lab_result_id }"
          :style="{ left: (dot.x - 22) + 'px', top: (dot.y - 22) + 'px' }"
          @click="emit('select', dot.point)"><view class="dot" /></button>
        <view v-for="dot in chart.dots" :key="'date-' + dot.point.lab_result_id" class="date"
          :style="{ left: (dot.x - 40) + 'px' }">
          <text>{{ dot.point.examination_date }}</text>
          <text>{{ dot.point.examination_time || '时间未记录' }}</text>
        </view>
      </view>
    </scroll-view>
    <text class="hint">点击数据点查看结果；长序列可左右滑动。</text>
  </view>
</template>
<style scoped>
.chart { display: flex; flex-direction: column; gap: 12px; }
.scroll { width: 100%; }
.plot { position: relative; height: 290px; border-bottom: 1px solid #ccc; }
.line { position: absolute; height: 2px; background: #087d44; transform-origin: left center; }
.point { position: absolute; width: 44px; height: 44px; padding: 0; margin: 0; background: transparent; display: flex; align-items: center; justify-content: center; }
.point::after { border: none; }
.dot { width: 10px; height: 10px; border: 2px solid #087d44; border-radius: 50%; background: white; }
.selected .dot { background: #087d44; width: 14px; height: 14px; }
.date { position: absolute; top: 224px; width: 80px; display: flex; flex-direction: column; text-align: center; font-size: 0.75em; }
.hint, .scale { color: #525b66; font-size: 0.875em; }
</style>
