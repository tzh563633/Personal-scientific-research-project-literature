<template>
  <section>
    <div class="toolbar">
      <div>
        <h2>文献分析</h2>
        <p>登记宿主机文件夹，由本地 Agent 扫描 PDF、导入解析并沉淀 Excel。</p>
      </div>
      <div class="toolbar-actions">
        <el-button @click="downloadExcel">下载 Excel</el-button>
        <el-button type="primary" @click="refreshAll">刷新状态</el-button>
      </div>
    </div>

    <el-card shadow="never" class="workspace-card">
      <template #header>
        <div class="card-header">
          <span>文件夹扫描</span>
          <el-button type="primary" @click="folderDialog = true">登记文件夹</el-button>
        </div>
      </template>
      <div class="folder-controls">
        <el-select
          v-model="selectedFolderId"
          placeholder="选择已登记的 PDF 文件夹"
          class="folder-select"
          @change="loadSelectedFolder"
        >
          <el-option
            v-for="folder in folders"
            :key="folder.id"
            :label="folder.name"
            :value="folder.id"
          />
        </el-select>
        <el-button :disabled="!selectedFolderId" @click="refreshFolder">
          查看文件
        </el-button>
        <el-button type="primary" :disabled="!selectedFolderId" :loading="scanRequested" @click="scanFolder">
          扫描并导入 PDF
        </el-button>
        <el-button
          type="danger"
          plain
          :disabled="!selectedFolderId"
          @click="removeFolder"
        >
          删除登记
        </el-button>
      </div>

      <el-descriptions v-if="selectedFolder" :column="2" size="small" border class="folder-summary">
        <el-descriptions-item label="文件夹路径">{{ selectedFolder.path }}</el-descriptions-item>
        <el-descriptions-item label="扫描范围">
          {{ selectedFolder.recursive ? '包含子文件夹' : '仅当前文件夹' }}
        </el-descriptions-item>
        <el-descriptions-item label="最近扫描">
          {{ selectedFolder.last_scan_at || '尚未扫描' }}
        </el-descriptions-item>
        <el-descriptions-item label="扫描任务">
          {{ scanJob ? `${scanJob.status} · ${scanJob.message || ''}` : '暂无' }}
        </el-descriptions-item>
      </el-descriptions>

      <el-empty v-if="selectedFolderId && !documents.length" description="此文件夹尚无已导入 PDF" />
      <el-table v-else-if="selectedFolderId" :data="documents" size="small" max-height="360">
        <el-table-column prop="file_name" label="PDF 文件" min-width="180" />
        <el-table-column prop="relative_path" label="相对路径" min-width="210" />
        <el-table-column label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
        </el-table-column>
        <el-table-column prop="modified_at" label="修改时间" min-width="165" />
        <el-table-column prop="import_status" label="导入" width="110" />
        <el-table-column prop="parse_status" label="解析" width="110" />
        <el-table-column prop="error" label="错误" min-width="180" />
      </el-table>
      <el-empty v-else description="登记一个本地 PDF 文件夹后开始扫描" />
    </el-card>

    <div class="analysis-grid">
      <el-card shadow="never">
        <template #header>单文件补充</template>
        <el-upload :http-request="upload" :show-file-list="false" accept=".pdf,.docx">
          <el-button type="primary">上传文献</el-button>
        </el-upload>
        <p class="muted">适合补充单篇 PDF 或 DOCX，批量文件请使用上方文件夹扫描。</p>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>Excel 更新</span>
            <el-button :loading="excelUpdating" @click="updateExcel">生成最新 Excel</el-button>
          </div>
        </template>
        <el-empty v-if="!excelUpdates.length" description="暂无 Excel 更新记录" />
        <el-table v-else :data="excelUpdates.slice(0, 4)" size="small">
          <el-table-column prop="update_time" label="时间" min-width="160" />
          <el-table-column prop="paper_count" label="文献" width="70" />
          <el-table-column prop="preserved_manual_count" label="人工保留" width="92" />
          <el-table-column prop="status" label="状态" width="80" />
        </el-table>
      </el-card>
    </div>

    <el-card shadow="never" class="workspace-card">
      <template #header>平台文献库</template>
      <el-table :data="papers" stripe>
        <el-table-column prop="title" label="标题" min-width="280" />
        <el-table-column prop="authors" label="作者" min-width="160" />
        <el-table-column prop="year" label="年份" width="90" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-button link type="primary" @click="show(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="folderDialog" title="登记本地 PDF 文件夹" width="560px">
      <el-form :model="folderForm" label-width="92px">
        <el-form-item label="显示名称">
          <el-input v-model="folderForm.name" placeholder="例如：区域数字韧性" />
        </el-form-item>
        <el-form-item label="Windows 路径">
          <el-input v-model="folderForm.path" placeholder="D:\论文\PDF" />
        </el-form-item>
        <el-form-item label="扫描范围">
          <el-switch v-model="folderForm.recursive" active-text="包含子文件夹" inactive-text="仅当前文件夹" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="folderDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingFolder" @click="createFolder">保存登记</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="drawer" title="文献详情" size="48%">
      <pre class="detail">{{ selected }}</pre>
    </el-drawer>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { waitForJob } from '../api'

const papers = ref([])
const folders = ref([])
const documents = ref([])
const excelUpdates = ref([])
const selectedFolderId = ref(null)
const scanJob = ref(null)
const folderDialog = ref(false)
const savingFolder = ref(false)
const scanRequested = ref(false)
const excelUpdating = ref(false)
const drawer = ref(false)
const selected = ref('')
const folderForm = reactive({ name: '', path: '', recursive: true, enabled: true })

const selectedFolder = computed(
  () => folders.value.find((folder) => folder.id === selectedFolderId.value) || null,
)

async function refreshAll() {
  try {
    const [paperResponse, folderResponse, excelResponse] = await Promise.all([
      api.get('/papers'),
      api.get('/folders'),
      api.get('/excel/updates'),
    ])
    papers.value = paperResponse.data
    folders.value = folderResponse.data
    excelUpdates.value = excelResponse.data
    if (!selectedFolderId.value && folders.value.length) {
      selectedFolderId.value = folders.value[0].id
    }
    await refreshFolder()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '文献分析状态加载失败')
  }
}

async function loadSelectedFolder() {
  scanJob.value = null
  await refreshFolder()
}

async function refreshFolder() {
  if (!selectedFolderId.value) {
    documents.value = []
    return
  }
  try {
    documents.value = (await api.get(`/folders/${selectedFolderId.value}/documents`)).data
    const folder = selectedFolder.value
    if (folder?.last_scan_job_id) {
      scanJob.value = (await api.get(`/jobs/${folder.last_scan_job_id}`)).data
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '文件夹内容加载失败')
  }
}

async function createFolder() {
  if (!folderForm.name.trim() || !folderForm.path.trim()) {
    ElMessage.warning('请填写名称和 Windows 路径')
    return
  }
  savingFolder.value = true
  try {
    const { data } = await api.post('/folders', {
      ...folderForm,
      name: folderForm.name.trim(),
      path: folderForm.path.trim(),
    })
    folderDialog.value = false
    Object.assign(folderForm, { name: '', path: '', recursive: true, enabled: true })
    await refreshAll()
    selectedFolderId.value = data.id
    await refreshFolder()
    ElMessage.success('文件夹已登记')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '文件夹登记失败')
  } finally {
    savingFolder.value = false
  }
}

async function scanFolder() {
  if (!selectedFolderId.value) return
  scanRequested.value = true
  try {
    const { data } = await api.post(`/folders/${selectedFolderId.value}/scan`, { max_files: 500 })
    scanJob.value = data
    ElMessage.success('扫描任务已提交，等待本地 Agent 处理')
    await refreshAll()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '扫描任务提交失败')
  } finally {
    scanRequested.value = false
  }
}

async function removeFolder() {
  if (!selectedFolderId.value) return
  try {
    await ElMessageBox.confirm('删除登记不会删除本机文件或已导入文献。', '确认删除')
    await api.delete(`/folders/${selectedFolderId.value}`)
    selectedFolderId.value = null
    scanJob.value = null
    await refreshAll()
    ElMessage.success('文件夹登记已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

async function upload({ file }) {
  const form = new FormData()
  form.append('file', file)
  try {
    await api.post('/papers/upload', form)
    ElMessage.success('已提交解析任务')
    await refreshAll()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '上传失败')
  }
}

async function updateExcel() {
  excelUpdating.value = true
  try {
    const { data } = await api.post('/excel/update')
    const job = await waitForJob(data.id)
    if (job.status === 'succeeded') {
      ElMessage.success('Excel 已更新，人工修正已保留')
    } else {
      ElMessage.error(job.error || 'Excel 更新失败')
    }
    await refreshAll()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Excel 更新失败')
  } finally {
    excelUpdating.value = false
  }
}

function show(row) {
  selected.value = JSON.stringify(row, null, 2)
  drawer.value = true
}

function formatSize(value) {
  if (!value) return '0 B'
  if (value < 1024 * 1024) return `${Math.round(value / 1024)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
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

onMounted(refreshAll)
</script>

<style scoped>
.workspace-card {
  margin-bottom: 18px;
}

.card-header,
.folder-controls {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.card-header {
  justify-content: space-between;
}

.folder-select {
  width: min(420px, 100%);
}

.folder-summary {
  margin: 16px 0;
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.muted {
  color: #667085;
  font-size: 13px;
  line-height: 1.5;
}

.detail {
  white-space: pre-wrap;
  font-family: ui-monospace, monospace;
}

@media (max-width: 760px) {
  .analysis-grid {
    grid-template-columns: 1fr;
  }
}
</style>
