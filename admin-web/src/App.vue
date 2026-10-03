<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { request } from './api'
import { setToken, token } from './auth'
import { activeAdminMenu } from './presentation'
const route = useRoute(), router = useRouter()
const activeMenu = computed(() => activeAdminMenu(route.path))
function logout() { setToken(''); void router.replace('/login') }
onMounted(() => {
  window.addEventListener('admin-session-expired', logout)
  if (token.value) void request('/me').catch(() => logout())
})
onUnmounted(() => window.removeEventListener('admin-session-expired', logout))
</script>
<template>
  <el-container class="shell">
    <el-header class="header"><div class="brand"><strong>检查单</strong><span>标准指标与 OCR 管理</span></div><el-button v-if="token" text @click="logout">退出登录</el-button></el-header>
    <el-container>
      <el-aside v-if="route.path !== '/login'" width="208px" class="admin-aside">
        <p class="aside-note">管理工作区</p>
        <el-menu router :default-active="activeMenu">
          <el-menu-item index="/">首页</el-menu-item>
          <el-menu-item index="/standard-metrics">标准指标</el-menu-item>
          <el-menu-item index="/metric-aliases">指标别名</el-menu-item>
          <el-menu-item index="/ocr-metric-issues">OCR 指标问题</el-menu-item>
          <el-menu-item index="/ocr-tasks">OCR 任务</el-menu-item>
        </el-menu>
      </el-aside>
      <el-main class="admin-main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>
