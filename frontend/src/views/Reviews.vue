<template>
  <section>
    <div class="toolbar">
      <div><h2>综述撰写</h2><p>结合大纲、Excel 和模型配置生成可追溯的文献综述。</p></div>
      <el-button type="primary" @click="createFramework">保存框架</el-button>
    </div>
    <el-card class="model-entry" shadow="never">
      <template #header>DeepSeek 模型入口</template>
      <el-form inline @submit.prevent>
        <el-form-item label="API Key">
          <el-input
            v-model="deepseekApiKey"
            type="password"
            show-password
            autocomplete="off"
            placeholder="输入后仅保留在当前页面"
            style="width: 360px"
          />
        </el-form-item>
        <el-checkbox v-model="saveDeepseekKey">加密保存到系统配置</el-checkbox>
        <el-button :disabled="!deepseekApiKey" @click="saveModelKey">保存入口配置</el-button>
      </el-form>
    </el-card>
    <el-form :model="form">
      <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="框架"><el-input v-model="form.content" type="textarea" :rows="8" /></el-form-item>
    </el-form>
    <el-divider />
    <el-table :data="frameworks" stripe>
      <el-table-column prop="name" label="框架" />
      <el-table-column label="操作" width="130">
        <template #default="{ row }"><el-button link type="primary" @click="generate(row.id)">生成</el-button></template>
      </el-table-column>
    </el-table>
    <el-divider />
    <el-table :data="outputs" stripe>
      <el-table-column prop="created_at" label="生成时间" width="200" />
      <el-table-column prop="missing_pdf_md_path" label="缺失提醒文件" />
      <el-table-column label="内容" min-width="300">
        <template #default="{ row }"><el-input :model-value="row.content" type="textarea" :rows="3" readonly /></template>
      </el-table-column>
    </el-table>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { waitForJob } from '../api'

const form = reactive({ name: '', content: '' })
const deepseekApiKey = ref('')
const saveDeepseekKey = ref(false)
const frameworks = ref([])
const outputs = ref([])
async function refresh() {
  frameworks.value = (await api.get('/reviews/frameworks')).data
  outputs.value = (await api.get('/reviews/outputs')).data
}
async function createFramework() {
  await api.post('/reviews/frameworks', form)
  Object.assign(form, { name: '', content: '' })
  await refresh()
}
async function saveModelKey() {
  if (!deepseekApiKey.value) return
  if (saveDeepseekKey.value) {
    await api.put('/system/config', { values: { DEEPSEEK_API_KEY: deepseekApiKey.value } })
    deepseekApiKey.value = ''
    ElMessage.success('DeepSeek API Key 已加密保存')
    return
  }
  ElMessage.success('API Key 已保留在当前页面')
}
async function generate(frameworkId) {
  const { data } = await api.post('/reviews/generate', { framework_id: frameworkId })
  const job = await waitForJob(data.id, { timeout: 30 * 60 * 1000 })
  if (job.status === 'succeeded') ElMessage.success('综述生成完成')
  else ElMessage.error(job.error || '综述生成失败')
  await refresh()
}
onMounted(refresh)
</script>

<style scoped>
.model-entry {
  margin-bottom: 18px;
}
</style>
