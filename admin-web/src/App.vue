<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { request } from './api'
import { setToken, token } from './auth'
const route = useRoute(), router = useRouter()
function logout() { setToken(''); void router.replace('/login') }
onMounted(() => {
  window.addEventListener('admin-session-expired', logout)
  if (token.value) void request('/me').catch(() => logout())
})
onUnmounted(() => window.removeEventListener('admin-session-expired', logout))
</script>
<template>
  <el-container class="shell">
    <el-header class="header"><strong>检查单管理后台</strong><el-button v-if="token" @click="logout">退出登录</el-button></el-header>
    <el-container>
      <el-aside v-if="route.path !== '/login'" width="200px">
        <el-menu router :default-active="route.path">
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/standard-metrics">标准指标</el-menu-item>
          <el-menu-item index="/metric-aliases">指标别名</el-menu-item>
          <el-menu-item index="/ocr-metric-issues">OCR 指标问题</el-menu-item>
          <el-menu-item index="/ocr-tasks">OCR 任务</el-menu-item>
        </el-menu>
      </el-aside>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.shell { min-height: 100vh; background: #f7f8fa; }
.header { display: flex; justify-content: space-between; align-items: center; background: #fff; border-bottom: 1px solid #e5e7eb; }
</style>
<style>
body { margin: 0; color: #303133; font-family: sans-serif; }
.toolbar { display: flex; gap: 12px; flex-wrap: wrap; margin: 16px 0; align-items: center; }
.toolbar .el-input { width: 260px; }
.toolbar .el-select { width: 170px; }
.el-alert { margin: 12px 0; }
.el-pagination { margin-top: 18px; }
h1 { font-size: 22px; }
</style>
