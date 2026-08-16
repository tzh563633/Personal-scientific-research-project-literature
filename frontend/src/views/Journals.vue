<template>
  <section>
    <div class="toolbar">
      <div>
        <h2>期刊追踪</h2>
        <p>追踪关注期刊和关键词的最新论文更新，查看抓取状态与提醒。</p>
      </div>
      <div class="toolbar-actions">
        <el-button @click="dialog = true">添加期刊</el-button>
        <el-button type="primary" :loading="monitoring" @click="run">立即监控</el-button>
      </div>
    </div>

    <div class="metric-grid journal-metrics">
      <div class="metric">
        <div class="metric-label">启用期刊</div>
        <div class="metric-value">{{ enabledCount }} / {{ journals.length }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">最近新增</div>
        <div class="metric-value">{{ items.length }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">关键词提醒</div>
        <div class="metric-value">{{ alerts.length }}</div>
      </div>
      <div class="metric">
        <div class="metric-label">抓取异常</div>
        <div class="metric-value">{{ errorCount }}</div>
      </div>
    </div>

    <el-card shadow="never" class="section-card">
      <template #header>期刊源</template>
      <el-table :data="journals" stripe>
        <el-table-column prop="name" label="期刊" min-width="170" />
        <el-table-column prop="rss_url" label="RSS" min-width="260" />
        <el-table-column prop="language" label="语言" width="80" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="toggleJournal(row)" />
          </template>
        </el-table-column>
        <el-table-column label="最近检查" min-width="165">
          <template #default="{ row }">{{ row.last_checked_at || '尚未检查' }}</template>
        </el-table-column>
        <el-table-column label="结果" width="92">
          <template #default="{ row }">
            <el-tag :type="row.last_error ? 'danger' : 'success'">
              {{ row.last_error ? '异常' : `${row.last_item_count || 0} 条` }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关键词" width="100">
          <template #default="{ row }">
            <el-button link type="primary" @click="openKeywords(row)">配置</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <div class="journal-columns">
      <el-card shadow="never">
        <template #header>最近论文</template>
        <el-empty v-if="!items.length" description="暂无抓取结果" />
        <el-table v-else :data="items" size="small" max-height="380">
          <el-table-column prop="title" label="标题" min-width="240" />
          <el-table-column prop="journal_name" label="期刊" min-width="140" />
          <el-table-column prop="authors" label="作者" min-width="140" />
          <el-table-column prop="created_at" label="入库时间" min-width="160" />
          <el-table-column label="链接" width="70">
            <template #default="{ row }">
              <el-link v-if="row.url" :href="row.url" target="_blank" type="primary">打开</el-link>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card shadow="never">
        <template #header>关键词提醒</template>
        <el-empty v-if="!alerts.length" description="暂无提醒" />
        <el-table v-else :data="alerts" size="small" max-height="380">
          <el-table-column prop="paper_title" label="论文" min-width="210" />
          <el-table-column prop="matched_keywords" label="命中词" min-width="130" />
          <el-table-column prop="created_at" label="时间" min-width="150" />
        </el-table>
      </el-card>
    </div>

    <el-dialog v-model="dialog" title="添加期刊">
      <el-form :model="form">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="RSS"><el-input v-model="form.rss_url" /></el-form-item>
        <el-form-item label="官网"><el-input v-model="form.url" /></el-form-item>
        <el-form-item label="语言"><el-input v-model="form.language" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="create">保存</el-button>
      </template>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api, { waitForJob } from '../api'

const journals = ref([])
const items = ref([])
const alerts = ref([])
const dialog = ref(false)
const keywordDrawer = ref(false)
const monitoring = ref(false)
const selectedJournal = ref(null)
const keywords = ref([])
const keywordText = ref('')
const form = reactive({ name: '', rss_url: '', url: '', language: 'en', enabled: true })

const enabledCount = computed(() => journals.value.filter((journal) => journal.enabled).length)
const errorCount = computed(() => journals.value.filter((journal) => journal.last_error).length)

async function refresh() {
  const [journalResponse, itemResponse, alertResponse] = await Promise.all([
    api.get('/journals'),
    api.get('/journals/items?limit=100'),
    api.get('/journals/alerts'),
  ])
  journals.value = journalResponse.data
  items.value = itemResponse.data
  alerts.value = alertResponse.data
}

async function create() {
  try {
    await api.post('/journals', form)
    dialog.value = false
    Object.assign(form, { name: '', rss_url: '', url: '', language: 'en', enabled: true })
    await refresh()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '期刊保存失败')
  }
}

async function toggleJournal(journal) {
  try {
    await api.put(`/journals/${journal.id}`, {
      name: journal.name,
      rss_url: journal.rss_url,
      url: journal.url,
      language: journal.language,
      enabled: journal.enabled,
    })
  } catch (error) {
    journal.enabled = !journal.enabled
    ElMessage.error(error.response?.data?.detail || '期刊状态更新失败')
  }
}

async function run() {
  monitoring.value = true
  try {
    const result = await api.post('/journals/monitor/run')
    const job = await waitForJob(result.data.id)
    if (job.status === 'succeeded') {
      ElMessage.success(`新增 ${job.result?.created || 0} 条，命中 ${job.result?.matched || 0} 条`)
    } else {
      ElMessage.error(job.error || '监控失败')
    }
    await refresh()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '监控失败')
  } finally {
    monitoring.value = false
  }
}

async function openKeywords(journal) {
  selectedJournal.value = journal
  keywordDrawer.value = true
  keywords.value = (await api.get(`/journals/${journal.id}/keywords`)).data
}

async function addKeyword() {
  if (!keywordText.value.trim() || !selectedJournal.value) return
  await api.post(`/journals/${selectedJournal.value.id}/keywords`, {
    keyword: keywordText.value.trim(),
  })
  keywordText.value = ''
  await openKeywords(selectedJournal.value)
}

async function removeKeyword(keyword) {
  await api.delete(`/journals/${selectedJournal.value.id}/keywords/${keyword.id}`)
  await openKeywords(selectedJournal.value)
}

onMounted(refresh)
</script>

<style scoped>
.journal-metrics {
  margin-bottom: 18px;
}

.section-card {
  margin-bottom: 18px;
}

.journal-columns {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.9fr);
  gap: 14px;
}

@media (max-width: 900px) {
  .journal-columns {
    grid-template-columns: 1fr;
  }
}
</style>
