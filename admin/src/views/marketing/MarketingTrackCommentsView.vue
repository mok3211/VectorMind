<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NCard, NDataTable, NInput, NSelect, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()
const loading = ref(false)
const items = ref<any[]>([])
const platform = ref<string | null>(null)
const keyword = ref<string | null>(null)
const mediaId = ref<string | null>(null)
const trackStatus = ref<number | null>(null)
const isDeleted = ref<string | null>(null)

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

async function reload() {
  loading.value = true
  try {
    const qs = new URLSearchParams()
    qs.set('page', String(pagination.page))
    qs.set('page_size', String(pagination.pageSize))
    if (platform.value) qs.set('platform', platform.value)
    if (mediaId.value?.trim()) qs.set('media_id', mediaId.value.trim())
    if (keyword.value?.trim()) qs.set('keyword', keyword.value.trim())
    if (trackStatus.value !== null) qs.set('track_status', String(trackStatus.value))
    if (isDeleted.value !== null) qs.set('is_deleted', isDeleted.value)
    const { data } = await api.get(`/api/marketing/track-comments?${qs.toString()}`)
    items.value = data.items
    pagination.itemCount = data.total ?? data.items?.length ?? 0
  } finally {
    loading.value = false
  }
}

async function removeOne(row: any) {
  await api.delete(`/api/marketing/track-comments/${row.id}`)
  message.success('已删除（软删）')
  await reload()
}

onMounted(reload)

const columns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '平台', key: 'platform', width: 90 },
  { title: 'media_id', key: 'platform_content_id', width: 220 },
  { title: '标题', key: 'title', minWidth: 320, ellipsis: { tooltip: true } },
  { title: '用户昵称', key: 'user_nickname', width: 180, ellipsis: { tooltip: true } },
  { title: '状态', key: 'track_status', width: 90 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render(row: any) {
      return h(NButton, { size: 'small', secondary: true, onClick: () => removeOne(row) }, { default: () => '删除' })
    }
  }
]
</script>

<template>
  <NCard size="small" class="sub">
    <template #header>评论监控池</template>
    <div class="row">
      <NSelect
        v-model:value="platform"
        clearable
        placeholder="平台"
        style="width: 160px"
        :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]"
      />
      <NInput v-model:value="mediaId" placeholder="media_id" style="width: 220px" />
      <NInput v-model:value="keyword" placeholder="关键词（标题/用户）" style="width: 220px" />
      <NSelect
        v-model:value="trackStatus"
        clearable
        placeholder="状态"
        style="width: 140px"
        :options="[
          { label: 'pending(0)', value: 0 },
          { label: 'updated(1)', value: 1 },
          { label: 'failed(2)', value: 2 }
        ]"
      />
      <NSelect
        v-model:value="isDeleted"
        clearable
        placeholder="删除"
        style="width: 140px"
        :options="[
          { label: '未删', value: 'false' },
          { label: '已删', value: 'true' }
        ]"
      />
      <div style="flex: 1" />
      <NButton secondary @click="reload">查询</NButton>
    </div>
    <div style="margin-top: 10px">
      <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="1080" remote :pagination="pagination" />
    </div>
  </NCard>
</template>

<style scoped>
.sub {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 14px;
}
.row {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
