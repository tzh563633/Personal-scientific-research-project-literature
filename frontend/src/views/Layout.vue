<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">科研控制平台</div>
      <el-menu
        router
        :default-active="$route.path"
        background-color="#172033"
        text-color="#dbeafe"
        active-text-color="#fff"
      >
        <el-menu-item index="/">控制台</el-menu-item>
        <el-menu-item index="/journal-tracking">期刊追踪</el-menu-item>
        <el-menu-item index="/folder-analysis">文献分析</el-menu-item>
        <el-menu-item index="/review-writing">综述撰写</el-menu-item>
        <el-menu-item index="/research-assets">研究资产</el-menu-item>
        <el-menu-item index="/system">系统设置</el-menu-item>
      </el-menu>
      <div class="secondary-nav">
        <span>平台工具</span>
        <el-button link type="info" @click="router.push('/commands')">任务指令</el-button>
      </div>
      <el-button link type="info" @click="logout">退出登录</el-button>
    </aside>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style scoped>
.secondary-nav {
  display: grid;
  gap: 4px;
  margin: 24px 10px 12px;
  color: #94a3b8;
  font-size: 12px;
}

.secondary-nav .el-button {
  justify-content: flex-start;
  padding: 0;
}
</style>
