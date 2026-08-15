<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">科研数据平台</div>
      <el-menu router :default-active="$route.path" background-color="#172033" text-color="#dbeafe" active-text-color="#fff">
        <el-menu-item index="/">总览</el-menu-item>
        <el-menu-item index="/papers">文献</el-menu-item>
        <el-menu-item index="/journals">期刊监控</el-menu-item>
        <el-menu-item index="/code">代码保管</el-menu-item>
        <el-menu-item index="/commands">远程指令</el-menu-item>
        <el-menu-item index="/reviews">文献综述</el-menu-item>
        <el-menu-item index="/system">系统配置</el-menu-item>
      </el-menu>
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

