<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NCard, NDataTable, NInput, NModal, NSelect, NText } from 'naive-ui'
import { api } from '@/lib/api'

const loading = ref(false)
const items = ref<any[]>([])

const show = ref(false)
const metricsLoading = ref(false)
const metrics = ref<any[]>([])
const current = ref<any | null>(null)

const platform = ref<string | null>(null)
const keyword = ref<string | null>(null)
const source = ref<string | null>(null)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  pageSizes: [20, 50, 100],
  itemCount: 0,
  showSizePicker: true,
  onChange: (p: number) => {
    pagination.page = p
    reload()
  },
  onUpdatePageSize: (s: number) => {
    pagination.pageSize = s
    pagination.page = 1
    reload()
  }
})

const metricsPagination = reactive({
  page: 1,
  pageSize: 20,
  pageSizes: [20, 50, 100],
  itemCount: 0,
  showSizePicker: true,
  onChange: (p: number) => {
    metricsPagination.page = p
    reloadMetrics()
  },
  onUpdatePageSize: (s: number) => {
    metricsPagination.pageSize = s
    metricsPagination.page = 1
    reloadMetrics()
  }
})

async function reload() {
  loading.value = true
  try {
    const qs = new URLSearchParams()
    qs.set('page', String(pagination.page))
    qs.set('page_size', String(pagination.pageSize))
    if (platform.value) qs.set('platform', platform.value)
    if (keyword.value?.trim()) qs.set('keyword', keyword.value.trim())
    if (source.value?.trim()) qs.set('source', source.value.trim())
    const { data } = await api.get(`/api/marketing/contents?${qs.toString()}`)
    items.value = data.items
    pagination.itemCount = data.total ?? data.items?.length ?? 0
  } finally {
    loading.value = false
  }
}

async function query() {
  pagination.page = 1
  await reload()
}

async function reloadMetrics() {
  const row = current.value
  if (!row?.id) return
  metricsLoading.value = true
  try {
    const qs = new URLSearchParams()
    qs.set('page', String(metricsPagination.page))
    qs.set('page_size', String(metricsPagination.pageSize))
    const { data } = await api.get(`/api/marketing/contents/${row.id}/metrics?${qs.toString()}`)
    metrics.value = data.items ?? []
    metricsPagination.itemCount = data.total ?? data.items?.length ?? 0
  } finally {
    metricsLoading.value = false
  }
}

async function openMetrics(row: any) {
  current.value = row
  show.value = true
  metricsPagination.page = 1
  metricsPagination.pageSize = 20
  await reloadMetrics()
}

onMounted(reload)

const columns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '平台', key: 'platform', width: 90 },
  { title: 'content_id', key: 'platform_content_id', width: 220 },
  { title: '标题', key: 'title', minWidth: 360, ellipsis: { tooltip: true } },
  { title: '来源', key: 'source', width: 200, ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
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
      <NInput v-model:value="keyword" placeholder="关键词（标题/作者/来源）" style="width: 260px" />
      <NInput v-model:value="source" placeholder="来源" style="width: 220px" />
      <div style="flex: 1" />
      <NButton secondary @click="query">查询</NButton>
    </div>
    <div style="margin-top: 10px">
      <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="1180" remote :pagination="pagination" />
    </div>
  </NCard>

  <NModal v-model:show="show" preset="card" title="指标快照" class="modal">
    <NText depth="3" style="display:block; margin-bottom: 8px">
      {{ current?.platform }} · {{ current?.platform_content_id }} · {{ current?.title }}
    </NText>
    <NDataTable
      :columns="metricColumns"
      :data="metrics"
      :scroll-x="720"
      :loading="metricsLoading"
      remote
      :pagination="metricsPagination"
    />
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
