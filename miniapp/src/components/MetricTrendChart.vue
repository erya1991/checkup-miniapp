<script setup lang="ts">
import { computed } from 'vue'
import { chartGeometry, chartDateLabel, examinationLabel, type TrendPoint } from '../profile-metrics'
const props = defineProps<{ points: TrendPoint[]; selectedId: string }>()
const emit = defineEmits<{ select: [point: TrendPoint] }>()
const chart = computed(() => chartGeometry(props.points))
// Geometry remains independent of medical data. Convert its logical coordinates
// to the shared 750rpx layout, including the page's WeChat font scale.
function position(value: number) { return `calc(${value * 2}rpx * var(--font-scale))` }
</script>
<template>
  <view class="chart">
    <text class="muted">数值范围：{{ chart.min }} ～ {{ chart.max }}</text>
    <scroll-view scroll-x class="scroll">
      <view class="plot" :style="{ width: position(chart.width) }">
        <view v-for="line in chart.lines" :key="line.id" class="line"
          :style="{ left: position(line.x), top: position(line.y), width: position(line.width), transform: 'rotate(' + line.angle + 'deg)' }" />
        <button v-for="dot in chart.dots" :key="dot.point.lab_result_id" class="point"
          :class="{ selected: selectedId === dot.point.lab_result_id }"
          :aria-label="examinationLabel(dot.point) + '，' + dot.point.result_text"
          :style="{ left: position(dot.x - 22), top: position(dot.y - 22) }"
          @click="emit('select', dot.point)"><view class="dot" /></button>
        <view v-for="dot in chart.dots" :key="'date-' + dot.point.lab_result_id" class="date"
          :style="{ left: position(dot.x - 40) }">
          <text>{{ chartDateLabel(dot.point).year }}</text>
          <text>{{ chartDateLabel(dot.point).date }}</text>
          <text v-if="chartDateLabel(dot.point).time">{{ chartDateLabel(dot.point).time }}</text>
        </view>
      </view>
    </scroll-view>
    <text class="muted">点击数据点查看本次结果；左右滑动可查看完整序列。</text>
  </view>
</template>
<style scoped>
.chart { display: flex; flex-direction: column; gap: 20rpx; }
.scroll { width: 100%; }
.plot { position: relative; height: calc(580rpx * var(--font-scale)); border-bottom: 1rpx solid var(--border); }
.line { position: absolute; height: 4rpx; background: var(--primary-text); transform-origin: left center; }
.point { position: absolute; width: calc(88rpx * var(--font-scale)); height: calc(88rpx * var(--font-scale)); min-height: 0; padding: 0; margin: 0; background: transparent; display: flex; align-items: center; justify-content: center; }
.point::after { border: none; }
.dot { width: calc(20rpx * var(--font-scale)); height: calc(20rpx * var(--font-scale)); border: 4rpx solid var(--primary-text); border-radius: 50%; background: var(--surface); }
.selected .dot { background: var(--primary-text); width: calc(28rpx * var(--font-scale)); height: calc(28rpx * var(--font-scale)); }
.date { position: absolute; top: calc(436rpx * var(--font-scale)); width: calc(160rpx * var(--font-scale)); display: flex; flex-direction: column; text-align: center; color: var(--muted); font-size: var(--font-note); line-height: 1.4; }
</style>
