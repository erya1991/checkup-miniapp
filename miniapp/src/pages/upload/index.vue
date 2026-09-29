<script setup lang="ts">
import { ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import { ensureLogin, request, type Ingestion, type Profile, type UploadAuthorization } from '../../api'
import { uploadImage } from '../../cos'

const id = ref('')
const forceNew = ref(false)
const ingestion = ref<Ingestion | null>(null)
const profileName = ref('')
const urls = ref<Record<string, string>>({})
const loading = ref(true)
const error = ref('')
const progress = ref(0)
const uploading = ref(false)
const failed = ref<{ path: string; size: number; mime: string }[]>([])

onLoad((params) => { id.value = params?.id || ''; forceNew.value = params?.new === '1' })
onShow(load)
async function load() {
  loading.value = true; error.value = ''
  try {
    const me = await ensureLogin()
    if (!me.default_health_profile_id) { error.value = '请先创建健康档案'; return }
    const profile = await request<Profile>(`/health-profiles/${me.default_health_profile_id}`)
    profileName.value = profile.display_name
    if (id.value) {
      ingestion.value = await request<Ingestion>(`/ingestions/${id.value}`)
      if (ingestion.value.health_profile_id !== me.default_health_profile_id) {
        error.value = '该任务属于其他档案，请切换回对应档案'; return
      }
    } else if (!forceNew.value) {
      const all = await request<Ingestion[]>('/ingestions')
      ingestion.value = all.find(i => i.health_profile_id === me.default_health_profile_id) || null
      if (ingestion.value) id.value = ingestion.value.id
    }
    await refreshPreviews()
  } catch (e) { error.value = e instanceof Error ? e.message : '加载失败' }
  finally { loading.value = false }
}
async function ensureIngestion() {
  if (id.value) return
  const me = await ensureLogin()
  const created = await request<Ingestion>('/ingestions', 'POST', {
    health_profile_id: me.default_health_profile_id, mode: 'OCR',
  })
  ingestion.value = created
  id.value = created.id
}
async function refresh() {
  ingestion.value = await request<Ingestion>(`/ingestions/${id.value}`)
  await refreshPreviews()
}
async function refreshPreviews() {
  if (!ingestion.value) return
  const next: Record<string, string> = {}
  for (const asset of ingestion.value.assets) {
    const signed = await request<{ url: string }>(`/ingestions/${id.value}/assets/${asset.id}/preview`)
    next[asset.id] = signed.url
  }
  urls.value = next
}
async function choose(sourceType: 'camera' | 'album') {
  try {
    const result = await uni.chooseImage({ count: 9, sourceType: [sourceType], sizeType: ['original'] })
    const tempFiles = Array.isArray(result.tempFiles) ? result.tempFiles : [result.tempFiles]
    const files = tempFiles.map((file, index) => ({
      path: result.tempFilePaths[index], size: file.size,
      mime: /\.png$/i.test(result.tempFilePaths[index]) ? 'image/png' : 'image/jpeg',
    }))
    for (const file of files) await upload(file)
  } catch (e) {
    if (!(e instanceof Error && e.message.includes('cancel'))) error.value = e instanceof Error ? e.message : '选图失败'
  }
}
async function upload(file: { path: string; size: number; mime: string }) {
  uploading.value = true; progress.value = 0; error.value = ''
  try {
    if (file.size <= 0 || file.size > 20_000_000) throw new Error('图片大小必须在 20 MB 以内')
    await ensureIngestion()
    const auth = await request<UploadAuthorization>(`/ingestions/${id.value}/upload-authorizations`, 'POST', { mime_type: file.mime })
    await uploadImage(auth, file.path, value => { progress.value = value })
    await request(`/ingestions/${id.value}/assets`, 'POST', {
      object_key: auth.object_key, mime_type: file.mime, file_size: file.size,
    })
    failed.value = failed.value.filter(f => f.path !== file.path)
    await refresh()
  } catch (e) {
    error.value = e instanceof Error ? e.message : '上传失败'
    if (!failed.value.some(f => f.path === file.path)) failed.value.push(file)
  } finally { uploading.value = false }
}
async function move(index: number, direction: number) {
  if (!ingestion.value) return
  const target = index + direction
  if (target < 0 || target >= ingestion.value.assets.length) return
  const ids = ingestion.value.assets.map(a => a.id)
  ;[ids[index], ids[target]] = [ids[target], ids[index]]
  try { ingestion.value = await request<Ingestion>(`/ingestions/${id.value}/assets/order`, 'PUT', { asset_ids: ids }) }
  catch (e) { error.value = e instanceof Error ? e.message : '排序失败' }
}
async function remove(assetId: string) {
  const confirmation = await uni.showModal({ title: '删除图片', content: '确认删除这张原始图片？' })
  if (!confirmation.confirm) return
  try {
    ingestion.value = await request<Ingestion>(`/ingestions/${id.value}/assets/${assetId}`, 'DELETE')
    await refreshPreviews()
  } catch (e) { error.value = e instanceof Error ? e.message : '删除失败' }
}
function preview(assetId: string) {
  const ordered = ingestion.value?.assets.map(a => urls.value[a.id]).filter(Boolean) || []
  if (ordered.length) uni.previewImage({ current: urls.value[assetId], urls: ordered })
}
</script>

<template>
  <view class="page">
    <text v-if="loading">加载任务和图片中...</text>
    <view v-else>
      <text>所属档案：{{ profileName }}</text>
      <text v-if="error" class="error">{{ error }}</text>
      <button v-if="error" @click="load">重新加载</button>
      <view v-if="ingestion">
        <text>导入状态：{{ ingestion.status }}</text>
        <text v-if="!ingestion.assets.length">请至少上传一张报告图片</text>
        <view v-for="(asset, index) in ingestion.assets" :key="asset.id" class="asset">
          <image :src="urls[asset.id]" mode="aspectFit" @click="preview(asset.id)" />
          <text>第 {{ asset.page_no }} 页 · 已上传</text>
          <button size="mini" :disabled="index === 0" @click="move(index, -1)">上移</button>
          <button size="mini" :disabled="index === ingestion.assets.length - 1" @click="move(index, 1)">下移</button>
          <button size="mini" @click="remove(asset.id)">删除</button>
        </view>
      </view>
      <text v-if="uploading">上传中 {{ progress }}%</text>
      <button :disabled="uploading" @click="choose('camera')">拍照上传</button>
      <button :disabled="uploading" @click="choose('album')">从相册选图/追加</button>
      <view v-for="file in failed" :key="file.path">
        <text>上传失败，可重试</text><button :disabled="uploading" @click="upload(file)">重试</button>
      </view>
      <text v-if="ingestion?.status === 'READY'">图片已准备好。下一阶段接入 OCR，本阶段不会开始识别。</text>
    </view>
  </view>
</template>

<style scoped>
.page { padding: 32rpx; display: flex; flex-direction: column; gap: 18rpx; }
.asset { display: flex; align-items: center; gap: 8rpx; padding: 12rpx 0; border-bottom: 1px solid #ddd; }
.asset image { width: 110rpx; height: 140rpx; }
.error { color: #b42318; }
</style>
