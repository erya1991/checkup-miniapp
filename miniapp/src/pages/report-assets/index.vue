<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { request, type Asset } from '../../api'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
interface Page extends Asset { url: string; loading: boolean; error: boolean; expiresAt: number }
const id = ref(''), pages = ref<Page[]>([]), loading = ref(false), error = ref('')
onLoad(q => { id.value = q?.id || ''; load() })
async function load() {
  if (loading.value) return
  loading.value = true; error.value = ''; pages.value = []
  try {
    if (!id.value) { error.value = '没有找到这份报告，请返回重新选择。'; return }
    const assets = await request<Asset[]>(`/reports/${encodeURIComponent(id.value)}/assets`)
    pages.value = assets.map(a => ({ ...a, url: '', loading: false, error: false, expiresAt: 0 }))
    await Promise.all(pages.value.map(preview))
  } catch (e) { error.value = userError(e, '原始报告暂时无法加载，请重试。') }
  finally { loading.value = false }
}
async function preview(page: Page) {
  if (page.loading) return
  page.loading = true; page.error = false; page.url = ''
  try {
    const result = await request<{ url: string; expires_in: number }>(`/reports/${encodeURIComponent(id.value)}/assets/${encodeURIComponent(page.id)}/preview`)
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
  <PageContainer>
    <text class="title">原始报告</text>
    <text class="muted">按报告页序展示。点击图片可放大，原图是最终核对依据。</text>
    <UiState v-if="loading" type="loading" title="正在加载原始报告" />
    <UiState v-if="error" type="error" title="原始报告加载失败" :description="error" action="重新加载" @action="load" />
    <UiState v-if="!loading && !error && !pages.length" type="empty" title="暂未找到原始图片" description="可以重新加载，或返回报告详情查看检验结果。" action="重新加载" @action="load" />
    <view v-for="page in pages" :key="page.id" class="card">
      <text class="section-title">第 {{ page.page_no }} 页</text>
      <UiState v-if="!loading && page.loading" type="loading" title="正在加载此页" />
      <UiState v-else-if="page.error" type="error" title="此页暂时无法加载" description="请检查网络后重试，其他已加载的图片仍可查看。" action="重试此页" @action="preview(page)" />
      <image v-else-if="page.url" :src="page.url" mode="widthFix" @error="page.error = true" @click="zoom(page)" />
    </view>
  </PageContainer>
</template>
<style scoped>
image { width: 100%; border-radius: 8rpx; }
</style>
