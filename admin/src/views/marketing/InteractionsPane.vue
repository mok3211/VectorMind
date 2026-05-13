<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NCard, NDataTable, NSelect, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

useMessage()
const items = ref<any[]>([])
const loading = ref(false)

const platform = ref<string | null>(null)
const eventType = ref<string | null>(null)
const status = ref<string | null>(null) // 'true' | 'false'

async function reload() {
  loading.value = true
  try {
    const qs = new URLSearchParams()
    qs.set('limit', '200')
    if (platform.value) qs.set('platform', platform.value)
    if (eventType.value) qs.set('event_type', eventType.value)
    if (status.value) qs.set('status', status.value)
    const { data } = await api.get(`/api/marketing/interaction-records?${qs.toString()}`)
    items.value = data.items
  } finally {
    loading.value = false
  }
}

onMounted(reload)

const columns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '平台', key: 'platform', width: 90 },
  { title: '事件', key: 'event_type', width: 140 },
  { title: '目标', key: 'target', width: 220 },
  { title: '结果', key: 'status', width: 90 },
  { title: '原因', key: 'reason' },
  { title: '时间', key: 'created_at', width: 220 }
]
</script>

<template>
  <NCard size="small" class="sub">
    <template #header>筛选</template>
    <div class="row">
      <NSelect
        v-model:value="platform"
        clearable
        placeholder="平台"
        style="width: 160px"
        :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]"
      />
      <NSelect
        v-model:value="eventType"
        clearable
        placeholder="事件"
        style="width: 200px"
        :options="[
          { label: '评论', value: 'send_comment' },
          { label: '私信', value: 'send_message' },
          { label: '点赞', value: 'like' }
        ]"
      />
      <NSelect
        v-model:value="status"
        clearable
        placeholder="结果"
        style="width: 160px"
        :options="[
          { label: '成功', value: 'true' },
          { label: '失败', value: 'false' }
        ]"
      />
      <div style="flex: 1" />
      <NButton secondary @click="reload">刷新</NButton>
    </div>
  </NCard>

  <NCard size="small" class="sub" style="margin-top: 12px">
    <template #header>互动记录</template>
    <NDataTable :columns="columns" :data="items" :loading="loading" />
  </NCard>
</template>

<style scoped>
.sub {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
}
.row {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
