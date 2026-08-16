<template>
  <section>
    <div class="toolbar">
      <div>
        <h2>研究资产</h2>
        <p>管理代码分支、安全审计、研究方法和研究工具，平台不会执行上传代码。</p>
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

        <el-tab-pane label="安全审计" name="security">
          <div class="dependency-summary">
            <el-tag type="danger">漏洞 {{ inspection.securityAudit.vulnerability_count }}</el-tag>
            <el-tag type="warning">最高 {{ inspection.securityAudit.highest_severity }}</el-tag>
            <el-tag type="warning">许可证复核 {{ inspection.securityAudit.license_review_count }}</el-tag>
            <el-tag type="danger">许可证限制 {{ inspection.securityAudit.license_restricted_count }}</el-tag>
            <span class="muted">未固定 {{ inspection.securityAudit.unpinned_count }}</span>
          </div>
          <el-table :data="inspection.securityAudit.findings" max-height="420">
            <el-table-column prop="name" label="依赖" min-width="150" />
            <el-table-column prop="manager" label="管理器" width="90" />
            <el-table-column label="版本" min-width="130">
              <template #default="{ row }">
                {{ row.version || row.specifier || '未固定' }}
              </template>
            </el-table-column>
            <el-table-column label="许可证" width="130">
              <template #default="{ row }">
                <el-tag :type="licenseType(row.license_status)">
                  {{ row.license_status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="漏洞" min-width="180">
              <template #default="{ row }">
                <div v-if="row.vulnerabilities?.length" class="vulnerability-list">
                  <el-tag
                    v-for="vulnerability in row.vulnerabilities"
                    :key="vulnerability.id"
                    :type="severityType(vulnerability.severity)"
                    effect="plain"
                  >
                    {{ vulnerability.id }}
                  </el-tag>
                </div>
                <span v-else class="muted">无</span>
              </template>
            </el-table-column>
            <el-table-column prop="recommendation" label="建议" min-width="220" />
          </el-table>
          <el-alert
            v-for="warning in inspection.securityAudit.warnings"
            :key="warning"
            :title="warning"
            type="warning"
            :closable="false"
            style="margin-top: 10px"
          />
        </el-tab-pane>

        <el-tab-pane label="文件树" name="tree">
          <div class="code-diff-toolbar">
            <el-input v-model="treePath" clearable placeholder="可选：进入相对目录" />
            <el-button @click="loadTree">
              <el-icon><FolderOpened /></el-icon>
              浏览目录
            </el-button>
          </div>
          <el-table :data="inspection.tree.entries" max-height="420">
            <el-table-column label="名称" min-width="220">
              <template #default="{ row }">
                <el-button v-if="row.kind === 'directory'" text @click="openTreeDirectory(row.path)">
                  <el-icon><Folder /></el-icon>
                  {{ row.name }}
                </el-button>
                <el-button v-else text @click="loadPreview(row.path)">
                  <el-icon><Document /></el-icon>
                  {{ row.name }}
                </el-button>
              </template>
            </el-table-column>
            <el-table-column prop="kind" label="类型" width="100" />
            <el-table-column prop="size_bytes" label="大小" width="120" />
            <el-table-column prop="path" label="路径" min-width="240" />
          </el-table>
          <el-tag v-if="inspection.tree.truncated" type="warning">目录结果已截断</el-tag>
          <el-alert
            v-for="warning in inspection.tree.warnings"
            :key="warning"
            :title="warning"
            type="warning"
            :closable="false"
            style="margin-top: 10px"
          />
          <el-alert
            v-if="inspection.preview?.redacted"
            title="预览内容包含疑似密钥，已脱敏"
            type="warning"
            :closable="false"
            style="margin-top: 12px"
          />
          <pre v-if="inspection.preview" class="code-diff">{{ inspection.preview.content }}</pre>
          <el-tag v-if="inspection.preview?.truncated" type="warning">预览已限制为 64 KB</el-tag>
        </el-tab-pane>

        <el-tab-pane label="检查报告" name="report">
          <div class="code-diff-toolbar">
            <el-button @click="loadReport">
              <el-icon><Memo /></el-icon>
              生成报告
            </el-button>
          </div>
          <pre class="code-report">{{ inspection.report?.markdown || '尚未生成报告' }}</pre>
        </el-tab-pane>
      </el-tabs>
    </el-drawer>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Folder, FolderOpened, Memo, Search, Upload, View } from '@element-plus/icons-vue'
import api from '../api'

const projects = ref([])
const drawer = ref(false)
const loading = ref(false)
const activeProject = ref(null)
const activeTab = ref('status')
const diffPath = ref('')
const treePath = ref('')
const inspection = reactive({
  status: null,
  commits: [],
  dependencies: { dependencies: [], high_risk_count: 0, review_count: 0, scanned_files: 0, warnings: [] },
  securityAudit: {
    findings: [],
    vulnerability_count: 0,
    highest_severity: 'none',
    license_review_count: 0,
    license_restricted_count: 0,
    unpinned_count: 0,
    warnings: [],
  },
  diff: null,
  commitDetail: null,
  tree: { entries: [], truncated: false, warnings: [] },
  preview: null,
  report: null,
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
  treePath.value = ''
  loading.value = true
  inspection.status = null
  inspection.commits = []
  inspection.diff = null
  inspection.commitDetail = null
  inspection.securityAudit = {
    findings: [],
    vulnerability_count: 0,
    highest_severity: 'none',
    license_review_count: 0,
    license_restricted_count: 0,
    unpinned_count: 0,
    warnings: [],
  }
  inspection.tree = { entries: [], truncated: false, warnings: [] }
  inspection.preview = null
  inspection.report = null
  try {
    const [status, commits, dependencies, securityAudit, tree] = await Promise.all([
      api.get(`/code/projects/${project.id}/git/status`),
      api.get(`/code/projects/${project.id}/git/commits`),
      api.get(`/code/projects/${project.id}/dependencies`),
      api.get(`/code/projects/${project.id}/security-audit`),
      api.get(`/code/projects/${project.id}/tree`),
    ])
    inspection.status = status.data
    inspection.commits = commits.data
    inspection.dependencies = dependencies.data
    inspection.securityAudit = securityAudit.data
    inspection.tree = tree.data
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

async function loadTree() {
  if (!activeProject.value) return
  try {
    inspection.tree = (
      await api.get(`/code/projects/${activeProject.value.id}/tree`, {
        params: treePath.value ? { path: treePath.value } : {},
      })
    ).data
    inspection.preview = null
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '目录获取失败')
  }
}

async function openTreeDirectory(path) {
  treePath.value = path
  await loadTree()
}

async function loadPreview(path) {
  if (!activeProject.value) return
  try {
    inspection.preview = (
      await api.get(`/code/projects/${activeProject.value.id}/files/preview`, {
        params: { path },
      })
    ).data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '文件预览失败')
  }
}

async function loadReport() {
  if (!activeProject.value) return
  try {
    inspection.report = (
      await api.get(`/code/projects/${activeProject.value.id}/inspection-report`)
    ).data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '报告生成失败')
  }
}

function riskType(level) {
  return { high: 'danger', review: 'warning', low: 'success' }[level] || 'info'
}

function licenseType(status) {
  return { restricted: 'danger', review: 'warning', allowed: 'success' }[status] || 'info'
}

function severityType(severity) {
  return { critical: 'danger', high: 'danger', medium: 'warning', low: 'info' }[severity] || 'info'
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

.code-report {
  max-height: 520px;
  overflow: auto;
  padding: 12px;
  background: #f8fafc;
  color: #0f172a;
  white-space: pre-wrap;
  word-break: break-word;
}

.dependency-summary {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.vulnerability-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.muted {
  color: #64748b;
  font-size: 12px;
}
</style>
