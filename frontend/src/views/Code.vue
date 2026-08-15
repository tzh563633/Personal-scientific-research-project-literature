<template>
  <section>
    <div class="toolbar">
      <div>
        <h2>代码保管</h2>
        <p>保存项目并查看 Git 状态与依赖清单，平台不会执行上传代码。</p>
      </div>
      <el-upload :http-request="upload" :show-file-list="false">
        <el-button type="primary">
          <el-icon><Upload /></el-icon>
          上传代码
        </el-button>
      </el-upload>
    </div>

    <el-table :data="projects" stripe style="margin-top: 18px" @row-click="inspect">
      <el-table-column prop="name" label="项目" min-width="180" />
      <el-table-column prop="description" label="描述" min-width="220" />
      <el-table-column prop="local_path" label="存储路径" min-width="220" />
      <el-table-column prop="created_at" label="上传时间" min-width="170" />
      <el-table-column label="检查" width="90" fixed="right">
        <template #default="{ row }">
          <el-tooltip content="查看项目检查结果">
            <el-button text circle @click.stop="inspect(row)">
              <el-icon><Search /></el-icon>
            </el-button>
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="drawer" :title="activeProject?.name || '项目检查'" size="720px">
      <el-skeleton v-if="loading" :rows="8" animated />
      <el-empty v-else-if="!activeProject" description="请选择项目" />
      <el-tabs v-else v-model="activeTab">
        <el-tab-pane label="Git 状态" name="status">
          <el-alert
            v-if="inspection.status?.error"
            :title="inspection.status.error"
            type="warning"
            :closable="false"
          />
          <el-descriptions v-else :column="2" border>
            <el-descriptions-item label="仓库可用">
              {{ inspection.status?.available ? '是' : '否' }}
            </el-descriptions-item>
            <el-descriptions-item label="分支">
              {{ inspection.status?.branch || '未识别' }}
            </el-descriptions-item>
            <el-descriptions-item label="工作区">
              <el-tag :type="inspection.status?.is_dirty ? 'warning' : 'success'">
                {{ inspection.status?.is_dirty ? '有未提交修改' : '干净' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="同步状态">
              ahead {{ inspection.status?.ahead || 0 }} / behind {{ inspection.status?.behind || 0 }}
            </el-descriptions-item>
          </el-descriptions>

          <div v-if="inspection.status?.changed_files?.length" class="code-list">
            <strong>变更文件</strong>
            <el-tag v-for="file in inspection.status.changed_files" :key="file" effect="plain">
              {{ file }}
            </el-tag>
          </div>

          <div class="code-diff-toolbar">
            <el-input v-model="diffPath" clearable placeholder="可选：查看某个相对路径的 diff" />
            <el-button @click="loadDiff">
              <el-icon><View /></el-icon>
              查看受限 diff
            </el-button>
          </div>
          <el-alert
            v-if="inspection.diff?.error"
            :title="inspection.diff.error"
            type="warning"
            :closable="false"
          />
          <pre v-else class="code-diff">{{ inspection.diff?.patch || '暂无 diff' }}</pre>
          <el-tag v-if="inspection.diff?.truncated" type="warning">diff 已限制为 200 KB</el-tag>
        </el-tab-pane>

        <el-tab-pane label="提交记录" name="commits">
          <el-empty v-if="!inspection.commits.length" description="暂无提交记录" />
          <el-timeline v-else>
            <el-timeline-item
              v-for="commit in inspection.commits"
              :key="commit.commit_hash"
              :timestamp="commit.authored_at || ''"
            >
              <el-button text @click="loadCommit(commit)">
                {{ commit.subject }}
              </el-button>
              <div class="muted">{{ commit.author }} · {{ commit.commit_hash.slice(0, 10) }}</div>
            </el-timeline-item>
          </el-timeline>
          <el-alert
            v-if="inspection.commitDetail?.error"
            :title="inspection.commitDetail.error"
            type="warning"
            :closable="false"
          />
          <pre v-else-if="inspection.commitDetail" class="code-diff">{{ inspection.commitDetail.patch }}</pre>
          <el-tag v-if="inspection.commitDetail?.truncated" type="warning">提交 diff 已限制为 200 KB</el-tag>
        </el-tab-pane>

        <el-tab-pane label="依赖风险" name="dependencies">
          <div class="dependency-summary">
            <el-tag type="danger">高风险 {{ inspection.dependencies.high_risk_count }}</el-tag>
            <el-tag type="warning">需复核 {{ inspection.dependencies.review_count }}</el-tag>
            <span class="muted">扫描文件 {{ inspection.dependencies.scanned_files }}</span>
          </div>
          <el-table :data="inspection.dependencies.dependencies" max-height="420">
            <el-table-column prop="name" label="依赖" min-width="150" />
            <el-table-column prop="manager" label="管理器" width="90" />
            <el-table-column prop="specifier" label="版本约束" min-width="130" />
            <el-table-column label="风险" width="110">
              <template #default="{ row }">
                <el-tag :type="riskType(row.risk_level)">{{ row.risk_level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="risk_reason" label="原因" min-width="180" />
          </el-table>
          <el-alert
            v-for="warning in inspection.dependencies.warnings"
            :key="warning"
            :title="warning"
            type="warning"
            :closable="false"
            style="margin-top: 10px"
          />
        </el-tab-pane>
      </el-tabs>
    </el-drawer>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Upload, View } from '@element-plus/icons-vue'
import api from '../api'

const projects = ref([])
const drawer = ref(false)
const loading = ref(false)
const activeProject = ref(null)
const activeTab = ref('status')
const diffPath = ref('')
const inspection = reactive({
  status: null,
  commits: [],
  dependencies: { dependencies: [], high_risk_count: 0, review_count: 0, scanned_files: 0, warnings: [] },
  diff: null,
  commitDetail: null,
})

async function refresh() {
  projects.value = (await api.get('/code/projects')).data
}

async function upload({ file }) {
  const form = new FormData()
  form.append('file', file)
  try {
    await api.post('/code/upload', form)
    ElMessage.success('代码已保存')
    await refresh()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '上传失败')
  }
}

async function inspect(project) {
  activeProject.value = project
  drawer.value = true
  activeTab.value = 'status'
  diffPath.value = ''
  loading.value = true
  inspection.status = null
  inspection.commits = []
  inspection.diff = null
  inspection.commitDetail = null
  try {
    const [status, commits, dependencies] = await Promise.all([
      api.get(`/code/projects/${project.id}/git/status`),
      api.get(`/code/projects/${project.id}/git/commits`),
      api.get(`/code/projects/${project.id}/dependencies`),
    ])
    inspection.status = status.data
    inspection.commits = commits.data
    inspection.dependencies = dependencies.data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '项目检查失败')
  } finally {
    loading.value = false
  }
}

async function loadDiff() {
  if (!activeProject.value) return
  try {
    inspection.diff = (
      await api.get(`/code/projects/${activeProject.value.id}/git/diff`, {
        params: diffPath.value ? { path: diffPath.value } : {},
      })
    ).data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'diff 获取失败')
  }
}

async function loadCommit(commit) {
  if (!activeProject.value) return
  try {
    inspection.commitDetail = (
      await api.get(
        `/code/projects/${activeProject.value.id}/git/commits/${commit.commit_hash}`,
      )
    ).data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '提交详情获取失败')
  }
}

function riskType(level) {
  return { high: 'danger', review: 'warning', low: 'success' }[level] || 'info'
}

onMounted(refresh)
</script>

<style scoped>
.code-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 18px 0;
}

.code-diff-toolbar {
  display: flex;
  gap: 8px;
  margin: 18px 0 10px;
}

.code-diff {
  max-height: 320px;
  overflow: auto;
  padding: 12px;
  background: #111827;
  color: #d1fae5;
  white-space: pre-wrap;
  word-break: break-word;
}

.dependency-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.muted {
  color: #64748b;
  font-size: 12px;
}
</style>
