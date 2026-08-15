<template>
  <section>
    <div class="toolbar">
      <div><h2>系统配置</h2><p>查看脱敏配置，真实密钥通过环境变量或配置接口注入。</p></div>
      <el-button type="primary" @click="load">刷新</el-button>
    </div>
    <el-descriptions :column="1" border>
      <el-descriptions-item v-for="(value, key) in config" :key="key" :label="key">{{ value }}</el-descriptions-item>
    </el-descriptions>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import api from '../api'
const config = ref({})
async function load() { config.value = (await api.get('/system/config')).data }
onMounted(load)
</script>

