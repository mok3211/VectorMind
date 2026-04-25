<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NCard, NDataTable, NTag, NText } from 'naive-ui'
import { api } from '@/lib/api'

const items = ref<any[]>([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get('/api/runs?limit=50')
    items.value = data.items
  } finally {
    loading.value = false
  }
})

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  {
    title: 'Agent',
    key: 'agent',
    width: 170,
    render(row: any) {
      return row.agent ? h(NTag, { size: 'small' }, { default: () => row.agent }) : '-'
    }
  },
  { title: 'Model', key: 'model', width: 180 },
  { title: 'Prompt', key: 'prompt_version', width: 120 },
  { title: 'Time', key: 'created_at' }
]
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>生成记录</template>
    <NText depth="3" style="display:block; margin-bottom: 10px">
      这里显示最近 50 条生成记录（用于复盘与迭代 prompt）。
    </NText>

    <NDataTable :columns="columns" :data="items" :loading="loading" />
  </NCard>
</template>

<style scoped>
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
</style>
