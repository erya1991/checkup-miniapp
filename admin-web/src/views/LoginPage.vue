<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorText, save } from '../api'
import { setToken } from '../auth'
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
  <el-card style="max-width: 440px; margin: 60px auto">
    <h1>管理员登录</h1>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-form label-position="top" @submit.prevent="submit">
      <el-form-item label="账号"><el-input v-model="username" autocomplete="username" maxlength="128" /></el-form-item>
      <el-form-item label="密码"><el-input v-model="password" type="password" show-password autocomplete="current-password" maxlength="2048" /></el-form-item>
      <el-button type="primary" native-type="submit" :loading="loading" :disabled="!username || !password">登录</el-button>
    </el-form>
  </el-card>
</template>
