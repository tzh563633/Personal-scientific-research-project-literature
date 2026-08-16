<template>
  <section>
    <div class="toolbar">
      <div>
        <h2>科研控制台</h2>
        <p>从期刊更新、文献分析、综述撰写到研究资产管理的统一入口。</p>
      </div>
      <el-button type="primary" @click="load">
        <el-icon><Refresh /></el-icon>
        刷新状态
      </el-button>
    </div>

    <div class="workflow-grid">
      <el-card
        v-for="card in workflowCards"
        :key="card.path"
        class="workflow-card"
        shadow="never"
      >
        <div class="workflow-card-header">
          <span class="workflow-icon"><el-icon><component :is="card.icon" /></el-icon></span>
          <el-tag :type="card.tagType" effect="plain">{{ card.metric }}</el-tag>
        </div>
        <h3>{{ card.title }}</h3>
        <p>{{ card.description }}</p>
        <el-button type="primary" link @click="$router.push(card.path)">
          进入页面
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </el-card>
    </div>

    <div class="metric-grid dashboard-metrics">
      <div class="metric">
        <div class="metric-label">文献总数</div>
        <div class="metric-value">{{ overview.paper_count }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">待处理文献</div>
        <div class="metric-value">{{ overview.pending_paper_count }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">期刊更新提醒</div>
        <div class="metric-value">{{ overview.alert_count }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">进行中任务</div>
        <div class="metric-value">{{ overview.active_job_count }}</div>
      </div>
    </div>

    <div class="dashboard-columns">
      <el-card shadow="never">
        <template #header>最近材料</template>
        <el-empty v-if="!overview.recent_papers.length" description="暂无材料" />
        <el-table v-else :data="overview.recent_papers" size="small">
          <el-table-column prop="title" label="标题" min-width="220" />
          <el-table-column prop="status" label="状态" width="110" />
          <el-table-column prop="updated_at" label="更新时间" min-width="170" />
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>系统状态</template>
        <el-descriptions :column="1" size="small">
          <el-descriptions-item label="启用期刊">
            {{ overview.enabled_journal_count }} / {{ overview.journal_count }}
          </el-descriptions-item>
          <el-descriptions-item label="综述输出">
            {{ overview.review_output_count }}
          </el-descriptions-item>
          <el-descriptions-item label="在线 Agent">
            {{ overview.online_agent_count }}
          </el-descriptions-item>
          <el-descriptions-item label="Excel 最近更新">
            {{ overview.latest_excel_update?.update_time || '暂无' }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </section>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowRight, Document, EditPen, FolderOpened, Refresh } from '@element-plus/icons-vue'
import api from '../api'

const overview = reactive({
  paper_count: 0,
  pending_paper_count: 0,
  alert_count: 0,
  active_job_count: 0,
  enabled_journal_count: 0,
  journal_count: 0,
  review_output_count: 0,
  online_agent_count: 0,
  latest_excel_update: null,
  recent_papers: [],
})

const workflowCards = [
  {
    path: '/journal-tracking',
    title: '期刊追踪',
    description: '追踪关注期刊和关键词的最新论文更新。',
    metric: '实时更新',
    tagType: 'success',
    icon: Document,
  },
  {
    path: '/folder-analysis',
    title: '文献分析',
    description: '导入指定文件夹，批量分析 PDF 并沉淀 Excel。',
    metric: '批量处理',
    tagType: 'warning',
    icon: FolderOpened,
  },
  {
    path: '/review-writing',
    title: '综述撰写',
    description: '结合大纲、Excel 和模型配置生成文献综述。',
    metric: 'DeepSeek',
    tagType: 'info',
    icon: EditPen,
  },
  {
    path: '/research-assets',
    title: '研究资产',
    description: '管理代码分支、研究方法和研究工具。',
    metric: '持续积累',
    tagType: 'danger',
    icon: FolderOpened,
  },
]

async function load() {
  try {
    Object.assign(overview, (await api.get('/dashboard/overview')).data)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '控制台状态加载失败')
  }
}

onMounted(load)
</script>

<style scoped>
.workflow-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.workflow-card {
  min-height: 190px;
}

.workflow-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.workflow-icon {
  color: #2563eb;
  font-size: 22px;
}

.workflow-card h3 {
  margin: 18px 0 8px;
}

.workflow-card p {
  min-height: 42px;
  color: #667085;
  line-height: 1.5;
}

.dashboard-metrics {
  margin-top: 18px;
}

.dashboard-columns {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(260px, 0.8fr);
  gap: 14px;
  margin-top: 18px;
}

@media (max-width: 1050px) {
  .workflow-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 700px) {
  .workflow-grid,
  .dashboard-columns {
    grid-template-columns: 1fr;
  }
}
</style>
