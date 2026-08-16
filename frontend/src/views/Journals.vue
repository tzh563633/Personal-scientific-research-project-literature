<template>
  <section>
    <div class="toolbar">
      <div><h2>期刊追踪</h2><p>追踪关注期刊和关键词的最新论文更新。</p></div>
      <div class="toolbar-actions">
        <el-button @click="dialog = true">添加期刊</el-button>
        <el-button type="primary" @click="run">立即监控</el-button>
      </div>
    </div>
    <el-table :data="journals" stripe>
      <el-table-column prop="name" label="期刊" min-width="180" />
      <el-table-column prop="rss_url" label="RSS" min-width="300" />
      <el-table-column prop="language" label="语言" width="90" />
      <el-table-column prop="enabled" label="启用" width="90" />
      <el-table-column label="关键词" width="110">
        <template #default="{ row }">
          <el-button link type="primary" @click="openKeywords(row)">配置</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="dialog" title="添加期刊">
      <el-form :model="form">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="RSS"><el-input v-model="form.rss_url" /></el-form-item>
        <el-form-item label="官网"><el-input v-model="form.url" /></el-form-item>
        <el-form-item label="语言"><el-input v-model="form.language" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="create">保存</el-button></template>
    </el-dialog>
    <el-drawer v-model="keywordDrawer" title="期刊关键词" size="360px">
      <el-form @submit.prevent>
        <el-form-item label="关键词">
          <el-input v-model="keywordText" @keyup.enter="addKeyword">
            <template #append><el-button @click="addKeyword">添加</el-button></template>
          </el-input>
        </el-form-item>
      </el-form>
      <el-tag v-for="keyword in keywords" :key="keyword.id" closable @close="removeKeyword(keyword)">
        {{ keyword.keyword }}
      </el-tag>
    </el-drawer>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { waitForJob } from '../api'

const journals = ref([])
const dialog = ref(false)
const keywordDrawer = ref(false)
const selectedJournal = ref(null)
const keywords = ref([])
const keywordText = ref('')
const form = reactive({ name: '', rss_url: '', url: '', language: 'en', enabled: true })
async function refresh() { journals.value = (await api.get('/journals')).data }
async function create() {
  await api.post('/journals', form)
  dialog.value = false
  Object.assign(form, { name: '', rss_url: '', url: '', language: 'en', enabled: true })
  await refresh()
}
async function run() {
  const result = await api.post('/journals/monitor/run')
  const job = await waitForJob(result.data.id)
  if (job.status === 'succeeded') {
    ElMessage.success(`新增 ${job.result?.created || 0} 条，命中 ${job.result?.matched || 0} 条`)
  } else {
    ElMessage.error(job.error || '监控失败')
  }
}
async function openKeywords(journal) {
  selectedJournal.value = journal
  keywordDrawer.value = true
  keywords.value = (await api.get(`/journals/${journal.id}/keywords`)).data
}
async function addKeyword() {
  if (!keywordText.value.trim() || !selectedJournal.value) return
  await api.post(`/journals/${selectedJournal.value.id}/keywords`, { keyword: keywordText.value.trim() })
  keywordText.value = ''
  await openKeywords(selectedJournal.value)
}
async function removeKeyword(keyword) {
  await api.delete(`/journals/${selectedJournal.value.id}/keywords/${keyword.id}`)
  await openKeywords(selectedJournal.value)
}
onMounted(refresh)
</script>
