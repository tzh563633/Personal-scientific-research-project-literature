<template>
  <section>
    <div class="toolbar">
      <div><h2>文献分析</h2><p>导入文献材料，查看解析状态并沉淀结构化结果。</p></div>
      <div class="toolbar-actions">
        <el-button @click="downloadExcel">下载 Excel</el-button>
        <el-button type="primary" @click="refresh">刷新</el-button>
      </div>
    </div>
    <el-upload :http-request="upload" :show-file-list="false" accept=".pdf,.docx">
      <el-button type="primary">上传文献</el-button>
    </el-upload>
    <el-table :data="papers" stripe style="margin-top: 18px">
      <el-table-column prop="title" label="标题" min-width="280" />
      <el-table-column prop="authors" label="作者" min-width="160" />
      <el-table-column prop="year" label="年份" width="90" />
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="show(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-drawer v-model="drawer" title="文献详情" size="48%">
      <pre class="detail">{{ selected }}</pre>
    </el-drawer>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const papers = ref([])
const drawer = ref(false)
const selected = ref('')

async function refresh() {
  papers.value = (await api.get('/papers')).data
}
async function upload({ file }) {
  const form = new FormData()
  form.append('file', file)
  try {
    await api.post('/papers/upload', form)
    ElMessage.success('已提交解析任务')
    await refresh()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '上传失败')
  }
}
function show(row) {
  selected.value = JSON.stringify(row, null, 2)
  drawer.value = true
}
async function downloadExcel() {
  const response = await api.get('/excel/download', { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'papers.xlsx'
  anchor.click()
  URL.revokeObjectURL(url)
}
onMounted(refresh)
</script>

<style scoped>
.detail {
  white-space: pre-wrap;
  font-family: ui-monospace, monospace;
}
</style>
