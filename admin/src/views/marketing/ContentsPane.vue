<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NButton, NCard, NDataTable, NModal, NSelect, NText } from 'naive-ui'
import { api } from '@/lib/api'

const loading = ref(false)
const items = ref<any[]>([])

const show = ref(false)
const metrics = ref<any[]>([])
const current = ref<any | null>(null)

const platform = ref<string | null>(null)

async function reload() {
  loading.value = true
  try {
    const qs = new URLSearchParams()
    qs.set('limit', '200')
    if (platform.value) qs.set('platform', platform.value)
    const { data } = await api.get(`/api/marketing/contents?${qs.toString()}`)
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function openMetrics(row: any) {
  current.value = row
  show.value = true
  const { data } = await api.get(`/api/marketing/contents/${row.id}/metrics?limit=50`)
  metrics.value = data.items
}

onMounted(reload)

const columns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '平台', key: 'platform', width: 90 },
  { title: 'content_id', key: 'platform_content_id', width: 220 },
  { title: '标题', key: 'title' },
  { title: '来源', key: 'source', width: 140 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render(row: any) {
      return h(NButton, { size: 'small', secondary: true, onClick: () => openMetrics(row) }, { default: () => '指标' })
    }
  }
]

const metricColumns = [
  { title: '时间', key: 'captured_at', width: 220 },
  { title: '播放', key: 'view_count', width: 90 },
  { title: '点赞', key: 'like_count', width: 90 },
  { title: '评论', key: 'comment_count', width: 90 },
  { title: '收藏', key: 'collect_count', width: 90 },
  { title: '分享', key: 'share_count', width: 90 }
]
</script>

<template>
  <NCard size="small" class="sub">
    <template #header>内容与指标</template>
    <div class="row">
      <NSelect
        v-model:value="platform"
        clearable
        placeholder="平台"
        style="width: 160px"
        :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]"
      />
      <div style="flex: 1" />
      <NButton secondary @click="reload">刷新</NButton>
    </div>
    <div style="margin-top: 10px">
      <NDataTable :columns="columns" :data="items" :loading="loading" />
    </div>
  </NCard>

  <NModal v-model:show="show" preset="card" title="指标快照" class="modal">
    <NText depth="3" style="display:block; margin-bottom: 8px">
      {{ current?.platform }} · {{ current?.platform_content_id }} · {{ current?.title }}
    </NText>
    <NDataTable :columns="metricColumns" :data="metrics" />
  </NModal>
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
.modal {
  width: min(920px, 96vw);
}
</style>
