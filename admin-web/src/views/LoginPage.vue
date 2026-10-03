<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorText, save } from '../api'
import { setToken } from '../auth'
import PageHeader from '../components/PageHeader.vue'
const username = ref(''), password = ref(''), loading = ref(false), error = ref('')
const router = useRouter()
async function submit() {
  if (loading.value) return
  loading.value = true; error.value = ''
  try {
    const data = await save<{ access_token: string }>('/auth/login', { username: username.value, password: password.value })
    setToken(data.access_token); password.value = ''; await router.replace('/')
  } catch (e) { error.value = errorText(e) }
  finally { loading.value = false }
}
</script>
<template>
  <el-card class="login-card">
    <PageHeader title="管理员登录" description="登录后维护标准指标与别名，查看 OCR 问题及只读任务。" />
    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="账号"><el-input v-model="username" autocomplete="username" maxlength="128" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="password" type="password" show-password autocomplete="current-password" maxlength="2048" /></el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" :disabled="!username || !password">登录</el-button>
    </el-form>
    <p class="login-note">请使用独立管理员账号。此工作区不提供用户健康报告内容编辑。</p>
  </el-card>
</template>
