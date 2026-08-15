<template>
  <section>
    <div class="toolbar">
      <div>
        <h2>工作台</h2>
        <p>查看科研资料处理状态和最近活动。</p>
      </div>
      <el-button type="primary" @click="load">刷新</el-button>
    </div>
    <div class="metric-grid">
      <div class="metric"><div class="metric-label">文献总数</div><div class="metric-value">{{ papers.length }}</div></div>
      <div class="metric"><div class="metric-label">已处理</div><div class="metric-value">{{ processed }}</div></div>
      <div class="metric"><div class="metric-label">期刊数量</div><div class="metric-value">{{ journals.length }}</div></div>
      <div class="metric"><div class="metric-label">综述输出</div><div class="metric-value">{{ outputs.length }}</div></div>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../api'

const papers = ref([])
const journals = ref([])
const outputs = ref([])
const processed = computed(() => papers.value.filter((paper) => paper.status === 'processed').length)

async function load() {
  const [paperResponse, journalResponse, outputResponse] = await Promise.all([
    api.get('/papers'),
    api.get('/journals'),
    api.get('/reviews/outputs'),
  ])
  papers.value = paperResponse.data
  journals.value = journalResponse.data
  outputs.value = outputResponse.data
}

onMounted(load)
</script>

