<script setup lang="ts">
import { ref } from 'vue'
import { onShow, onHide } from '@dcloudio/uni-app'
import { ensureLogin, request, type Profile } from '../../api'
import { requestGuard } from '../../profile-metrics'
import { navigate } from '../../navigation'
import { userError } from '../../ui'
import PageContainer from '../../components/PageContainer.vue'
import ProfileContext from '../../components/ProfileContext.vue'
import UiState from '../../components/UiState.vue'
const loading = ref(true), error = ref(''), profile = ref<Profile | null>(null)
const guard = requestGuard()
onShow(load); onHide(() => guard.invalidate())
async function load() {
  const run = guard.next(); loading.value = true; error.value = ''; profile.value = null
  try {
    const me = await ensureLogin()
    if (!me.default_health_profile_id || !guard.current(run)) return
    const current = await request<Profile>(`/health-profiles/${me.default_health_profile_id}`)
    if (guard.current(run)) profile.value = current
  } catch (e) { if (guard.current(run)) error.value = userError(e) }
  finally { if (guard.current(run)) loading.value = false }
}
</script>
<template>
  <PageContainer>
    <UiState v-if="loading" type="loading" title="正在加载档案" />
    <UiState v-else-if="error" type="error" title="暂时无法加载" :description="error" action="重试" @action="load" />
    <ProfileContext v-else-if="profile" :name="profile.display_name" @choose="navigate('/pages/profiles/index')" />
    <UiState v-else type="empty" title="还没有健康档案" description="先为自己创建档案，也可管理家人的报告。" action="创建本人档案" @action="navigate('/pages/profile-edit/index')" />
    <button class="secondary" @click="navigate('/pages/profiles/index')">管理健康档案</button>
    <view class="card"><text class="section-title">数据与隐私</text><text class="muted">每位家人的报告、指标历史与关注状态按健康档案分别保存。原始报告仅供你核对查看。</text><text class="muted">可在报告或健康档案管理中永久删除数据。删除前会说明影响范围，操作不可恢复。</text></view>
    <view class="card"><text class="section-title">关于检查单</text><text class="muted">用于整理个人和家人的检验报告、查看指标历史与趋势。不提供医疗诊断、疾病风险预测或用药建议。</text><text class="muted">原始检验报告始终是最终核对依据。</text></view>
  </PageContainer>
</template>
