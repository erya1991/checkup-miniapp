<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { request, type Asset } from '../../api'
interface Page extends Asset { url: string; loading: boolean; error: boolean; expiresAt: number }
const id = ref('')
const pages = ref<Page[]>([])
const loading = ref(false)
const error = ref('')
onLoad(q => { id.value = q?.id || ''; load() })
async function load() {
  loading.value = true; error.value = ''; pages.value = []
  try {
    const assets = await request<Asset[]>(`/reports/${id.value}/assets`)
    pages.value = assets.map(a => ({ ...a, url: '', loading: false, error: false, expiresAt: 0 }))
    await Promise.all(pages.value.map(preview))
  } catch (e) { error.value = e instanceof Error ? e.message : '原始报告暂时无法加载，请重试。' }
  finally { loading.value = false }
}
async function preview(page: Page) {
  page.loading = true; page.error = false; page.url = ''
  try {
    const result = await request<{ url: string; expires_in: number }>(`/reports/${id.value}/assets/${page.id}/preview`)
    page.url = result.url; page.expiresAt = Date.now() + result.expires_in * 1000
  } catch { page.error = true }
  finally { page.loading = false }
}
async function zoom(page: Page) {
  if (Date.now() >= page.expiresAt) await preview(page)
  if (!page.url || page.error) return
  uni.previewImage({ current: page.url, urls: pages.value.filter(p => p.url && !p.error).map(p => p.url),
    fail: () => { page.error = true } })
}
</script>
<template>
  <view class="page">
    <text v-if="loading">正在加载原始报告...</text>
    <view v-if="error"><text>{{ error }}</text><button @click="load">重试</button></view>
    <text v-if="!loading && !error && !pages.length">未找到原始报告图片。</text>
    <view v-for="page in pages" :key="page.id" class="card">
      <text>第 {{ page.page_no }} 页</text>
      <text v-if="page.loading">正在加载...</text>
      <view v-else-if="page.error"><text>原始报告暂时无法加载，请重试。</text><button @click="preview(page)">重试此页</button></view>
      <image v-else-if="page.url" :src="page.url" mode="widthFix" @error="page.error = true" @click="zoom(page)" />
    </view>
  </view>
</template>
<style scoped>
.page, .card { display: flex; flex-direction: column; gap: 20rpx; padding: 32rpx; }
image { width: 100%; }
</style>
