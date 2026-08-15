<template>
  <section>
    <div class="toolbar">
      <div><h2>远程指令</h2><p>输入业务指令，系统只允许已登记的业务动作。</p></div>
    </div>
    <el-input v-model="text" type="textarea" :rows="4" placeholder="例如：更新 Excel、立即监控期刊、执行备份" />
    <el-button type="primary" style="margin-top: 12px" @click="submit">提交</el-button>
    <el-table :data="commands" stripe style="margin-top: 18px">
      <el-table-column prop="text" label="指令" min-width="260" />
      <el-table-column prop="intent" label="意图" width="160" />
      <el-table-column prop="status" label="状态" width="120" />
      <el-table-column prop="error" label="错误" />
    </el-table>
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const text = ref('')
const commands = ref([])
let poller

async function refresh() {
  try {
    commands.value = (await api.get('/commands')).data
  } catch {
    // Authentication and global request errors are handled by the API interceptor.
  }
}
async function submit() {
  if (!text.value.trim()) return
  try {
    const { data } = await api.post('/commands', { text: text.value })
    commands.value = [data, ...commands.value]
    text.value = ''
    if (data.status === 'failed') ElMessage.warning(data.error || '指令未登记')
    else ElMessage.success('指令已进入 Agent 队列')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '提交失败')
  }
}
onMounted(async () => {
  await refresh()
  poller = window.setInterval(refresh, 3000)
})
onBeforeUnmount(() => window.clearInterval(poller))
</script>
