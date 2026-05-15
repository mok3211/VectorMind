<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NCard, NDataTable, NInput, NSelect, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()
const loading = ref(false)
const items = ref<any[]>([])
const platform = ref<string | null>(null)
const keyword = ref<string | null>(null)
const source = ref<string | null>(null)
const mediaId = ref<string | null>(null)
const status = ref<number | null>(null)
const isComment = ref<string | null>(null)

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
    if (keyword.value?.trim()) qs.set('keyword', keyword.value.trim())
    if (source.value?.trim()) qs.set('source', source.value.trim())
    if (mediaId.value?.trim()) qs.set('platform_content_id', mediaId.value.trim())
    if (status.value !== null) qs.set('status', String(status.value))
    if (isComment.value !== null) qs.set('is_comment', isComment.value)
    const { data } = await api.get(`/api/marketing/track-media?${qs.toString()}`)
    items.value = data.items
    pagination.itemCount = data.total ?? data.items?.length ?? 0
  } finally {
    loading.value = false
  }
}

async function toggleComment(row: any) {
  await api.put(`/api/marketing/track-media/${row.id}/toggle-comment?enable=${!row.is_comment}`)
  await reload()
}

async function sendComment(row: any) {
  const text = window.prompt('请输入要发送的评论内容：', '路过支持一下～')
  if (!text) return
  const { data } = await api.post('/api/marketing/send-comment', {
    platform: row.platform,
    track_media_id: row.id,
    text,
    headless: false,
    slow_mo_ms: 200
  })
  if (data.ok) message.success('已提交评论（请到互动记录查看结果）')
  else message.error(`评论失败：${data.detail}`)
  await reload()
}

onMounted(reload)

const columns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '平台', key: 'platform', width: 90 },
  { title: 'media_id', key: 'platform_content_id', width: 220 },
  { title: '标题', key: 'title', minWidth: 320, ellipsis: { tooltip: true } },
  { title: '来源', key: 'source', width: 200, ellipsis: { tooltip: true } },
  { title: '评论维护', key: 'is_comment', width: 110 },
  { title: '状态', key: 'status', width: 90 },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right' as const,
    render(row: any) {
      return h('div', { style: 'display:flex; gap:8px' }, [
        h(
          NButton,
          { size: 'small', secondary: true, onClick: () => toggleComment(row) },
          { default: () => (row.is_comment ? '关闭评论维护' : '开启评论维护') }
        ),
        h(NButton, { size: 'small', type: 'primary', secondary: true, onClick: () => sendComment(row) }, { default: () => '评论' })
      ])
    }
  }
]
</script>

<template>
  <NCard size="small" class="sub">
    <template #header>内容监控池</template>
    <div class="row">
      <NSelect
        v-model:value="platform"
        clearable
        placeholder="平台"
        style="width: 160px"
        :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]"
      />
      <NInput v-model:value="mediaId" placeholder="media_id" style="width: 220px" />
      <NInput v-model:value="keyword" placeholder="关键词（标题/keyword）" style="width: 220px" />
      <NInput v-model:value="source" placeholder="来源" style="width: 200px" />
      <NSelect
        v-model:value="status"
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
        v-model:value="isComment"
        clearable
        placeholder="评论维护"
        style="width: 140px"
        :options="[
          { label: '开启', value: 'true' },
          { label: '关闭', value: 'false' }
        ]"
      />
      <div style="flex: 1" />
      <NButton secondary @click="reload">查询</NButton>
    </div>
    <div style="margin-top: 10px">
      <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="1220" remote :pagination="pagination" />
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
