<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onShow, onHide, onUnload } from '@dcloudio/uni-app'
import { ensureLogin, request, type Ingestion, type Profile, type UploadAuthorization } from '../../api'
import { uploadImage } from '../../cos'
import { requestGuard } from '../../profile-metrics'
import { taskStatusLabels } from '../../ingestion-tasks'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import UiState from '../../components/UiState.vue'
import StatusTag from '../../components/StatusTag.vue'
import { navigate } from '../../navigation'
import { registerAndRefresh } from '../../upload-flow'

const id = ref('')
const ingestion = ref<Ingestion | null>(null)
const profileName = ref('')
const urls = ref<Record<string, string>>({})
const loading = ref(true)
const error = ref('')
const progress = ref(0)
const uploading = ref(false)
const failed = ref<{ path: string; size: number; mime: string }[]>([])
const recognizing = ref(false)
const manualizing = ref(false)
const authorized = ref(false), profileId = ref(''), managing = ref(false), choosing = ref(false)
const previewErrors = ref<Record<string, boolean>>({})
const guard = requestGuard()
let visible = false
const editable = computed(() => authorized.value && (!ingestion.value || ['UPLOADING', 'READY'].includes(ingestion.value.status)))
const blocked = computed(() => uploading.value || recognizing.value || manualizing.value || managing.value || choosing.value)

onLoad((params) => { id.value = params?.id || '' })
onShow(() => { visible = true; if (!blocked.value) load() })
onHide(() => { visible = false; if (!blocked.value) guard.invalidate() })
onUnload(() => { visible = false; guard.invalidate() })
async function load() {
  if (blocked.value) return
  const run = guard.next()
  loading.value = true; error.value = ''; authorized.value = false; ingestion.value = null; urls.value = {}; profileName.value = ''; profileId.value = ''
  try {
    const me = await ensureLogin()
    if (!me.default_health_profile_id) { error.value = '请先创建健康档案'; return }
    const profile = await request<Profile>(`/health-profiles/${me.default_health_profile_id}`)
    if (!guard.current(run)) return
    profileId.value = profile.id
    profileName.value = profile.display_name
    if (id.value) {
      const value = await request<Ingestion>(`/ingestions/${id.value}`)
      if (!guard.current(run)) return
      if (value.health_profile_id !== me.default_health_profile_id) {
        error.value = '这份报告属于其他档案，请切换回对应档案'; return
      }
      ingestion.value = value
    }
    authorized.value = true
    await refreshPreviews(run)
  } catch (e) { if (guard.current(run)) error.value = userError(e) }
  finally { if (guard.current(run)) loading.value = false }
}
async function ensureIngestion() {
  if (id.value) return
  if (!authorized.value || !profileId.value) throw new Error('PROFILE_REQUIRED')
  const created = await request<Ingestion>('/ingestions', 'POST', {
    health_profile_id: profileId.value, mode: 'OCR',
  })
  ingestion.value = created
  id.value = created.id
}
async function refresh() {
  ingestion.value = await request<Ingestion>(`/ingestions/${id.value}`)
  await refreshPreviews()
}
async function refreshPreviews(run?: number) {
  if (!ingestion.value) return
  const currentId = ingestion.value.id
  const currentAssets = ingestion.value.assets
  const next: Record<string, string> = {}
  const errors: Record<string, boolean> = {}
  for (const asset of currentAssets) {
    try {
      const signed = await request<{ url: string }>(`/ingestions/${currentId}/assets/${asset.id}/preview`)
      next[asset.id] = signed.url
    } catch { errors[asset.id] = true }
  }
  if (ingestion.value?.id !== currentId || (run !== undefined && !guard.current(run))) return
  urls.value = next; previewErrors.value = errors
}
async function retryPreview(assetId: string) {
  try {
    const signed = await request<{ url: string }>(`/ingestions/${id.value}/assets/${assetId}/preview`)
    urls.value[assetId] = signed.url; previewErrors.value[assetId] = false
  } catch { previewErrors.value[assetId] = true }
}
async function choose(sourceType: 'camera' | 'album') {
  if (!editable.value || blocked.value) return
  choosing.value = true
  try {
    const result = await uni.chooseImage({ count: 9, sourceType: [sourceType], sizeType: ['original'] })
    const tempFiles = Array.isArray(result.tempFiles) ? result.tempFiles : [result.tempFiles]
    const files = tempFiles.map((file, index) => ({
      path: result.tempFilePaths[index], size: file.size,
      mime: /\.png$/i.test(result.tempFilePaths[index]) ? 'image/png' : 'image/jpeg',
    }))
    for (const file of files) await upload(file)
  } catch (e) {
    if (!String((e as { errMsg?: string })?.errMsg || '').includes('cancel')) error.value = userError(e, '未能选择图片，请重新拍照或从相册选择。')
  } finally { choosing.value = false }
}
async function upload(file: { path: string; size: number; mime: string }) {
  if (!editable.value) return
  uploading.value = true; progress.value = 0; error.value = ''
  try {
    if (file.size <= 0 || file.size > 20_000_000) throw new Error('图片大小必须在 20 MB 以内')
    await ensureIngestion()
    const auth = await request<UploadAuthorization>(`/ingestions/${id.value}/upload-authorizations`, 'POST', { mime_type: file.mime })
    await uploadImage(auth, file.path, value => { progress.value = value })
    const outcome = await registerAndRefresh(() => request(`/ingestions/${id.value}/assets`, 'POST', {
      object_key: auth.object_key, mime_type: file.mime, file_size: file.size,
    }), refresh)
    failed.value = failed.value.filter(f => f.path !== file.path)
    if (outcome.refreshRequired) error.value = '图片已上传，但列表暂时未刷新。请重新加载，不需要重复上传这张图片。'
  } catch (e) {
    error.value = file.size <= 0 || file.size > 20_000_000 ? '图片大小必须在 20 MB 以内，请重新选择。' : userError(e, '图片未完成上传，请重试。')
    if (!failed.value.some(f => f.path === file.path)) failed.value.push(file)
  } finally { uploading.value = false }
}
async function move(index: number, direction: number) {
  if (!ingestion.value || !editable.value || blocked.value) return
  const target = index + direction
  if (target < 0 || target >= ingestion.value.assets.length) return
  const ids = ingestion.value.assets.map(a => a.id)
  ;[ids[index], ids[target]] = [ids[target], ids[index]]
  managing.value = true
  try { ingestion.value = await request<Ingestion>(`/ingestions/${id.value}/assets/order`, 'PUT', { asset_ids: ids }) }
  catch (e) { error.value = userError(e, '未能调整页序，请重试。') }
  finally { managing.value = false }
}
async function remove(assetId: string) {
  if (!editable.value || blocked.value) return
  managing.value = true
  try {
    const confirmation = await uni.showModal({ title: '删除图片', content: '确认删除这张原始图片？' })
    if (!confirmation.confirm) return
    ingestion.value = await request<Ingestion>(`/ingestions/${id.value}/assets/${assetId}`, 'DELETE')
    await refreshPreviews()
  } catch (e) { error.value = userError(e, '未能删除图片，请重试。') }
  finally { managing.value = false }
}
async function preview(assetId: string) {
  await refreshPreviews()
  const ordered = ingestion.value?.assets.map(a => urls.value[a.id]).filter(Boolean) || []
  if (urls.value[assetId]) {
    try { await uni.previewImage({ current: urls.value[assetId], urls: ordered }) }
    catch { previewErrors.value[assetId] = true }
  }
}
async function recognize() {
  if (!ingestion.value || ingestion.value.status !== 'READY' || blocked.value) return
  recognizing.value = true; error.value = ''
  try {
    await request(`/ingestions/${id.value}/recognize`, 'POST')
    if (!visible) return
    ingestion.value = await request<Ingestion>(`/ingestions/${id.value}`)
    if (!visible) return
    uni.redirectTo({ url: `/pages/ocr/index?id=${encodeURIComponent(id.value)}` })
  } catch (e) { error.value = userError(e, '未能开始识别，请重试。') }
  finally { recognizing.value = false }
}
function showOcr() {
  const page = ingestion.value?.status === 'PENDING_CONFIRMATION' ? 'confirmation' : 'ocr'
  uni.redirectTo({ url: `/pages/${page}/index?id=${encodeURIComponent(id.value)}` })
}
async function manual() {
  if (blocked.value || !authorized.value || !['READY', 'OCR_FAILED'].includes(ingestion.value?.status || '')) return
  manualizing.value = true; error.value = ''
  try {
    await request(`/ingestions/${id.value}/manual`, 'POST')
    if (!visible) return
    uni.redirectTo({ url: `/pages/confirmation/index?id=${encodeURIComponent(id.value)}` })
  } catch (e) { error.value = userError(e, '未能进入手工录入，请重试。') }
  finally { manualizing.value = false }
}
</script>

<template>
  <PageContainer>
    <UiState v-if="loading" type="loading" title="正在加载报告图片" />
    <template v-else>
      <text class="section-title">所属档案：{{ profileName || '尚未选择' }}</text>
      <UiState v-if="error" type="error" title="操作未完成" :description="error" :action="blocked ? '' : authorized ? '重新加载' : '选择健康档案'" @action="authorized ? load() : navigate('/pages/profiles/index')" />
      <template v-if="authorized">
        <view class="section-heading"><text class="title">上传报告图片</text><StatusTag v-if="ingestion" :label="taskStatusLabels[ingestion.status] || '报告处理中'" /></view>
        <text class="muted">上传 → 识别 → 核对 → 正式保存</text>
        <UiState v-if="!ingestion?.assets.length" type="empty" title="选择清晰的检验报告图片" description="一份报告可上传多页图片。开始识别前，可追加图片或调整页序。" />
        <view v-for="(asset, index) in ingestion?.assets || []" :key="asset.id" class="card asset">
          <image v-if="urls[asset.id] && !previewErrors[asset.id]" :src="urls[asset.id]" mode="aspectFit" @click="preview(asset.id)" @error="previewErrors[asset.id] = true" />
          <UiState v-else type="error" title="图片暂时无法显示" action="重试图片" @action="retryPreview(asset.id)" />
          <view class="asset-info">
            <text class="section-title">第 {{ asset.page_no }} 页</text><text class="muted">已上传 · 点击图片查看大图</text>
            <view v-if="editable" class="actions">
              <button class="secondary" size="mini" :disabled="blocked || index === 0" @click="move(index, -1)">上移</button>
              <button class="secondary" size="mini" :disabled="blocked || index === ingestion!.assets.length - 1" @click="move(index, 1)">下移</button>
              <button class="danger" size="mini" :disabled="blocked" @click="remove(asset.id)">移除</button>
            </view>
          </view>
        </view>
        <view v-if="uploading" class="card"><text>正在上传图片 · {{ progress }}%</text><progress :percent="progress" activeColor="#07c160" /></view>
        <view v-if="editable" class="actions">
          <button class="secondary" :disabled="blocked" @click="choose('camera')">拍照</button>
          <button class="secondary" :disabled="blocked" @click="choose('album')">从相册选择 / 追加</button>
        </view>
        <view v-for="file in (editable ? failed : [])" :key="file.path" class="card">
          <text class="error">这张图片上传未完成</text><button class="secondary" :disabled="blocked" @click="upload(file)">重试上传</button>
        </view>
        <button v-if="ingestion?.status === 'READY'" class="primary" :loading="recognizing" :disabled="blocked" @click="recognize">开始识别</button>
        <button v-if="['READY', 'OCR_FAILED'].includes(ingestion?.status || '')" class="text-action" :disabled="blocked" @click="manual">保留原图，手工录入</button>
        <view v-if="ingestion && !editable" class="card">
          <text class="muted">已进入识别，原图可继续预览，图片内容与页序已锁定。</text>
          <button v-if="ingestion.status !== 'CONFIRMED'" class="primary" @click="showOcr">{{ ingestion.status === 'PENDING_CONFIRMATION' ? '核对报告' : '查看识别状态' }}</button>
          <text v-else>报告已保存，可在“报告”中查看。</text>
        </view>
      </template>
    </template>
  </PageContainer>
</template>
<style scoped>
.asset { display: flex; flex-direction: row; flex-wrap: wrap; align-items: center; gap: 24rpx; }
.asset image { width: 160rpx; height: 200rpx; }
.asset-info { flex: 1; min-width: 280rpx; display: flex; flex-direction: column; gap: 12rpx; }
</style>
