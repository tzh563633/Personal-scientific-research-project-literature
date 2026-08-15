<template>
  <main class="auth-page">
    <section class="auth-panel">
      <h1>初始化管理员</h1>
      <p>仅在系统尚未创建用户时可用。</p>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">创建管理员</el-button>
      </el-form>
      <el-button link @click="$router.push('/login')">返回登录</el-button>
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
    await api.post('/setup/admin', form)
    ElMessage.success('初始化完成，请登录')
    router.push('/login')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '初始化失败')
  } finally {
    loading.value = false
  }
}
</script>

