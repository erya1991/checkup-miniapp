<template>
  <el-container class="shell">
    <el-header class="header">检查单管理后台</el-header>
    <el-main><router-view /></el-main>
  </el-container>
</template>

<style scoped>
.shell { min-height: 100vh; background: #f7f8fa; }
.header { display: flex; align-items: center; background: #fff; border-bottom: 1px solid #e5e7eb; font-weight: 600; }
</style>
