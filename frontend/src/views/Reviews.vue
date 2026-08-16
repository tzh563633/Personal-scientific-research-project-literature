<template>
  <section>
    <div class="toolbar">
      <div><h2>综述撰写</h2><p>结合大纲、指定 Excel 和模型配置生成可追溯的文献综述。</p></div>
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
      <el-form-item label="指定 Excel">
        <el-select v-model="form.excel_path" clearable placeholder="选择平台内 Excel" style="width: 480px">
          <el-option :value="null" label="不指定，按大纲检索平台文献" />
          <el-option
            v-for="file in excelFiles"
            :key="file.path"
            :label="`${file.name} (${formatSize(file.size_bytes)})`"
            :value="file.path"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <el-divider />
    <el-table :data="frameworks" stripe>
      <el-table-column prop="name" label="框架" />
      <el-table-column prop="excel_path" label="Excel" min-width="220">
        <template #default="{ row }">{{ row.excel_path || '按大纲检索' }}</template>
      </el-table-column>
      <el-table-column label="操作" width="130">
        <template #default="{ row }"><el-button link type="primary" @click="generate(row.id)">生成</el-button></template>
      </el-table-column>
    </el-table>
    <el-divider />
    <el-table :data="outputs" stripe>
      <el-table-column prop="created_at" label="生成时间" width="200" />
      <el-table-column prop="verified_source_count" label="已核实来源" width="110" />
      <el-table-column prop="full_text_source_count" label="有全文" width="85" />
      <el-table-column label="事实核查" min-width="130">
        <template #default="{ row }">
          {{ row.fact_check_summary ? `${row.fact_check_summary.passed}/${row.fact_check_summary.checked}` : '暂无' }}
        </template>
      </el-table-column>
      <el-table-column prop="missing_pdf_md_path" label="缺失提醒文件" />
      <el-table-column label="来源" width="90">
        <template #default="{ row }">
          <el-button link type="primary" @click="viewSources(row)">查看</el-button>
        </template>
      </el-table-column>
      <el-table-column label="内容" min-width="300">
        <template #default="{ row }"><el-input :model-value="row.content" type="textarea" :rows="3" readonly /></template>
      </el-table-column>
    </el-table>
    <el-drawer v-model="sourceDrawer" title="综述来源" size="680px">
      <el-empty v-if="!reviewSources.length" description="暂无来源" />
      <el-table v-else :data="reviewSources" size="small">
        <el-table-column prop="title" label="题名" min-width="240" />
        <el-table-column prop="source_type" label="来源" width="100" />
        <el-table-column prop="verified" label="核实" width="80">
          <template #default="{ row }">{{ row.verified ? '已核实' : '待核实' }}</template>
        </el-table-column>
        <el-table-column prop="full_text_available" label="全文" width="80">
          <template #default="{ row }">{{ row.full_text_available ? '已下载' : '缺失' }}</template>
        </el-table-column>
        <el-table-column prop="doi" label="DOI" min-width="170" />
      </el-table>
    </el-drawer>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { waitForJob } from '../api'

const form = reactive({ name: '', content: '', excel_path: null })
const deepseekApiKey = ref('')
const saveDeepseekKey = ref(false)
const frameworks = ref([])
const outputs = ref([])
const excelFiles = ref([])
const sourceDrawer = ref(false)
const reviewSources = ref([])
async function refresh() {
  const [frameworkResponse, outputResponse, excelResponse] = await Promise.all([
    api.get('/reviews/frameworks'),
    api.get('/reviews/outputs'),
    api.get('/excel/files'),
  ])
  frameworks.value = frameworkResponse.data
  outputs.value = outputResponse.data
  excelFiles.value = excelResponse.data
  if (!form.excel_path && excelFiles.value.length) {
    form.excel_path = excelFiles.value[0].path
  }
}
async function createFramework() {
  await api.post('/reviews/frameworks', form)
  Object.assign(form, { name: '', content: '', excel_path: excelFiles.value[0]?.path || null })
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
  const framework = frameworks.value.find((item) => item.id === frameworkId)
  const payload = {
    framework_id: frameworkId,
    excel_path: framework?.excel_path || null,
  }
  if (deepseekApiKey.value) payload.deepseek_api_key = deepseekApiKey.value
  const { data } = await api.post('/reviews/generate', payload)
  const job = await waitForJob(data.id, { timeout: 30 * 60 * 1000 })
  if (job.status === 'succeeded') ElMessage.success('综述生成完成')
  else ElMessage.error(job.error || '综述生成失败')
  if (!saveDeepseekKey.value) deepseekApiKey.value = ''
  await refresh()
}
async function viewSources(output) {
  reviewSources.value = (await api.get(`/reviews/outputs/${output.id}/sources`)).data
  sourceDrawer.value = true
}
function formatSize(value) {
  if (!value) return '0 B'
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}
onMounted(refresh)
</script>

<style scoped>
.model-entry {
  margin-bottom: 18px;
}
</style>
