<template>
  <section>
    <div class="toolbar">
      <div><h2>文献综述</h2><p>保存综述框架，基于已解析文献和公开学术源生成 Markdown。</p></div>
      <el-button type="primary" @click="createFramework">保存框架</el-button>
    </div>
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
async function generate(frameworkId) {
  const { data } = await api.post('/reviews/generate', { framework_id: frameworkId })
  const job = await waitForJob(data.id, { timeout: 30 * 60 * 1000 })
  if (job.status === 'succeeded') ElMessage.success('综述生成完成')
  else ElMessage.error(job.error || '综述生成失败')
  await refresh()
}
onMounted(refresh)
</script>
