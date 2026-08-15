<template>
  <main class="auth-page">
    <section class="auth-panel">
      <h1>科研数据平台</h1>
      <p>登录本地研究工作台</p>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">登录</el-button>
      </el-form>
      <el-button link @click="$router.push('/setup')">首次启动初始化</el-button>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function submit() {
  loading.value = true
  try {
    const { data } = await api.post('/auth/login', form)
    localStorage.setItem('token', data.access_token)
    router.push('/')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

