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

    <el-tabs v-model="assetLibraryTab" class="asset-library">
      <el-tab-pane label="研究方法" name="methods">
        <div class="asset-toolbar">
          <span class="muted">保存适用场景、步骤、优缺点和关联材料。</span>
          <el-button type="primary" @click="openAssetDialog('method')">新增方法</el-button>
        </div>
        <el-table :data="methods" size="small">
          <el-table-column prop="name" label="方法" min-width="180" />
          <el-table-column prop="use_cases" label="适用场景" min-width="220" />
          <el-table-column prop="steps" label="关键步骤" min-width="260" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="openAssetDialog('method', row)">编辑</el-button>
              <el-button link type="danger" @click="removeAsset('method', row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="研究工具" name="tools">
        <div class="asset-toolbar">
          <span class="muted">保存工具用途、安装方式、使用说明和注意事项。</span>
          <el-button type="primary" @click="openAssetDialog('tool')">新增工具</el-button>
        </div>
        <el-table :data="tools" size="small">
          <el-table-column prop="name" label="工具" min-width="180" />
          <el-table-column prop="purpose" label="用途" min-width="240" />
          <el-table-column prop="installation" label="安装方式" min-width="220" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="openAssetDialog('tool', row)">编辑</el-button>
              <el-button link type="danger" @click="removeAsset('tool', row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="分析流程" name="workflows">
        <div class="asset-toolbar">
          <span class="muted">保存可复用的研究流程模板。</span>
          <el-button type="primary" @click="openAssetDialog('workflow')">新增流程</el-button>
        </div>
        <el-table :data="workflows" size="small">
          <el-table-column prop="name" label="流程" min-width="180" />
          <el-table-column prop="description" label="说明" min-width="260" />
          <el-table-column label="步骤" min-width="280">
            <template #default="{ row }">{{ row.steps?.join(' -> ') || '暂无步骤' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" @click="openAssetDialog('workflow', row)">编辑</el-button>
              <el-button link type="danger" @click="removeAsset('workflow', row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="assetDialog" :title="assetDialogTitle" width="620px">
      <el-form :model="assetForm" label-width="94px">
        <el-form-item label="名称">
          <el-input v-model="assetForm.name" />
        </el-form-item>
        <template v-if="assetType === 'method'">
          <el-form-item label="说明"><el-input v-model="assetForm.description" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="适用场景"><el-input v-model="assetForm.use_cases" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="关键步骤"><el-input v-model="assetForm.steps" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="优势"><el-input v-model="assetForm.advantages" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="局限"><el-input v-model="assetForm.limitations" type="textarea" :rows="2" /></el-form-item>
        </template>
        <template v-else-if="assetType === 'tool'">
          <el-form-item label="用途"><el-input v-model="assetForm.purpose" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="安装方式"><el-input v-model="assetForm.installation" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="使用说明"><el-input v-model="assetForm.usage" type="textarea" :rows="3" /></el-form-item>
          <el-form-item label="注意事项"><el-input v-model="assetForm.cautions" type="textarea" :rows="2" /></el-form-item>
        </template>
        <template v-else>
          <el-form-item label="说明"><el-input v-model="assetForm.description" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="流程步骤">
            <el-input v-model="assetForm.steps" type="textarea" :rows="5" placeholder="每行一个步骤" />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="assetDialog = false">取消</el-button>
        <el-button type="primary" @click="saveAsset">保存</el-button>
      </template>
    </el-dialog>

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

        <el-tab-pane label="Git 分支" name="branches">
          <el-alert
            v-if="inspection.branchError"
            :title="inspection.branchError"
            type="warning"
            :closable="false"
          />
          <div class="code-diff-toolbar">
            <el-input v-model="branchName" placeholder="新分支名称，例如 research/review-draft" />
            <el-button type="primary" :disabled="!branchName" @click="createBranch">创建分支</el-button>
          </div>
          <el-table :data="inspection.branches" size="small">
            <el-table-column prop="name" label="分支" min-width="260" />
            <el-table-column prop="commit_hash" label="提交" min-width="160" />
            <el-table-column label="当前" width="85">
              <template #default="{ row }">
                <el-tag :type="row.current ? 'success' : 'info'">{{ row.current ? '当前' : '可用' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <p class="muted">平台只创建 Git 引用，不检出分支或执行项目代码。</p>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Folder, FolderOpened, Memo, Search, Upload, View } from '@element-plus/icons-vue'
import api from '../api'

const projects = ref([])
const methods = ref([])
const tools = ref([])
const workflows = ref([])
const assetLibraryTab = ref('methods')
const assetDialog = ref(false)
const assetType = ref('method')
const assetEditingId = ref(null)
const assetForm = reactive({
  name: '',
  description: '',
  use_cases: '',
  steps: '',
  advantages: '',
  limitations: '',
  purpose: '',
  installation: '',
  usage: '',
  cautions: '',
})
const drawer = ref(false)
const loading = ref(false)
const activeProject = ref(null)
const activeTab = ref('status')
const diffPath = ref('')
const treePath = ref('')
const branchName = ref('')
const inspection = reactive({
  status: null,
  branches: [],
  branchError: null,
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
const assetDialogTitle = computed(() => {
  const labels = { method: '研究方法', tool: '研究工具', workflow: '分析流程' }
  return `${assetEditingId.value ? '编辑' : '新增'}${labels[assetType.value]}`
})

async function refresh() {
  const [projectResponse, methodResponse, toolResponse, workflowResponse] = await Promise.all([
    api.get('/code/projects'),
    api.get('/research-assets/methods'),
    api.get('/research-assets/tools'),
    api.get('/research-assets/workflows'),
  ])
  projects.value = projectResponse.data
  methods.value = methodResponse.data
  tools.value = toolResponse.data
  workflows.value = workflowResponse.data
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
  inspection.branches = []
  inspection.branchError = null
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
    const [status, branches, commits, dependencies, securityAudit, tree] = await Promise.all([
      api.get(`/code/projects/${project.id}/git/status`),
      api.get(`/code/projects/${project.id}/git/branches`),
      api.get(`/code/projects/${project.id}/git/commits`),
      api.get(`/code/projects/${project.id}/dependencies`),
      api.get(`/code/projects/${project.id}/security-audit`),
      api.get(`/code/projects/${project.id}/tree`),
    ])
    inspection.status = status.data
    inspection.branches = branches.data
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

async function createBranch() {
  if (!activeProject.value || !branchName.value.trim()) return
  try {
    const { data } = await api.post(`/code/projects/${activeProject.value.id}/git/branches`, {
      name: branchName.value.trim(),
    })
    inspection.branches = [...inspection.branches, data].sort((left, right) => left.name.localeCompare(right.name))
    branchName.value = ''
    ElMessage.success('分支已创建')
  } catch (error) {
    inspection.branchError = error.response?.data?.detail || '分支创建失败'
  }
}

function assetPath(type) {
  return { method: 'methods', tool: 'tools', workflow: 'workflows' }[type]
}

function resetAssetForm() {
  Object.assign(assetForm, {
    name: '',
    description: '',
    use_cases: '',
    steps: '',
    advantages: '',
    limitations: '',
    purpose: '',
    installation: '',
    usage: '',
    cautions: '',
  })
}

function openAssetDialog(type, item = null) {
  assetType.value = type
  assetEditingId.value = item?.id || null
  resetAssetForm()
  if (item) {
    Object.assign(assetForm, item)
    if (type === 'workflow') assetForm.steps = (item.steps || []).join('\n')
  }
  assetDialog.value = true
}

function assetPayload() {
  if (assetType.value === 'workflow') {
    return {
      name: assetForm.name,
      description: assetForm.description || null,
      steps: assetForm.steps.split('\n').map((item) => item.trim()).filter(Boolean),
    }
  }
  if (assetType.value === 'tool') {
    return {
      name: assetForm.name,
      purpose: assetForm.purpose || null,
      installation: assetForm.installation || null,
      usage: assetForm.usage || null,
      cautions: assetForm.cautions || null,
    }
  }
  return {
    name: assetForm.name,
    description: assetForm.description || null,
    use_cases: assetForm.use_cases || null,
    steps: assetForm.steps || null,
    advantages: assetForm.advantages || null,
    limitations: assetForm.limitations || null,
  }
}

async function saveAsset() {
  if (!assetForm.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  const path = `/research-assets/${assetPath(assetType.value)}`
  try {
    if (assetEditingId.value) {
      await api.put(`${path}/${assetEditingId.value}`, assetPayload())
    } else {
      await api.post(path, assetPayload())
    }
    assetDialog.value = false
    await refresh()
    ElMessage.success('研究资产已保存')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  }
}

async function removeAsset(type, item) {
  try {
    await ElMessageBox.confirm(`删除“${item.name}”不会影响已上传代码或文献。`, '确认删除')
    await api.delete(`/research-assets/${assetPath(type)}/${item.id}`)
    await refresh()
    ElMessage.success('研究资产已删除')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(error.response?.data?.detail || '删除失败')
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

.asset-library {
  margin-top: 22px;
}

.asset-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
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
