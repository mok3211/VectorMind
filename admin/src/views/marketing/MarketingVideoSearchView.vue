<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NDataTable, NInput, NInputNumber, NSelect, NTag, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

const router = useRouter()
const message = useMessage()

const platform = ref<'xhs' | 'douyin'>('xhs')
const keyword = ref('')
const page = ref(1)
const loading = ref(false)
const items = ref<any[]>([])

async function search() {
  if (!keyword.value.trim()) return message.error('请输入关键词')
  loading.value = true
  try {
    const { data } = await api.post('/api/marketing/search/videos', {
      platform: platform.value,
      keyword: keyword.value.trim(),
      page: page.value,
      timeout_ms: 60_000
    })
    items.value = data.items ?? []
  } catch (e: any) {
    const detail = e?.response?.data?.detail ?? e?.message ?? '搜索失败'
    message.error(String(detail))
  } finally {
    loading.value = false
  }
}

async function ingest(row: any) {
  try {
    await api.post('/api/marketing/track-media', {
      platform: row.platform,
      platform_content_id: row.platform_content_id,
      url: row.url || null,
      title: row.title || null,
      source: `search:${keyword.value.trim()}`,
      source_type: 'external',
      create_user: null,
      is_comment: true
    })
    message.success('已收录到内容监控池')
  } catch (e: any) {
    const detail = e?.response?.data?.detail ?? e?.message ?? '收录失败'
    message.error(String(detail))
  }
}

function openUrl(row: any) {
  const u = row.url || ''
  if (u) window.open(u, '_blank')
}

onMounted(() => {})

const columns = [
  { title: '平台', key: 'platform', width: 90, render: (r: any) => h(NTag, { size: 'small' }, { default: () => r.platform }) },
  { title: '标题', key: 'title', minWidth: 360, ellipsis: { tooltip: true } },
  { title: '作者', key: 'author_name', width: 200, ellipsis: { tooltip: true } },
  { title: 'content_id', key: 'platform_content_id', width: 240 },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right' as const,
    render(row: any) {
      return h('div', { style: 'display:flex; gap:8px' }, [
        h(NButton, { size: 'small', secondary: true, onClick: () => openUrl(row) }, { default: () => '打开' }),
        h(NButton, { size: 'small', tertiary: true, onClick: () => ingest(row) }, { default: () => '收录' })
      ])
    }
  }
]
</script>

<template>
  <div class="wrap">
    <NCard size="small" class="sub">
      <template #header>视频搜索</template>
      <div class="bar">
        <NSelect
          v-model:value="platform"
          style="width: 160px"
          :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]"
        />
        <NInput v-model:value="keyword" placeholder="输入关键词（需要先有该平台的 Session）" />
        <NInputNumber v-model:value="page" :min="1" :max="10" style="width: 140px" />
        <NButton type="primary" :loading="loading" @click="search">搜索</NButton>
        <NButton secondary @click="router.push('/marketing/sessions')">去扫码登录</NButton>
      </div>
    </NCard>

    <NCard size="small" class="sub">
      <template #header>搜索结果</template>
      <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="1240" />
    </NCard>
  </div>
</template>

<style scoped>
.wrap {
  display: grid;
  gap: 12px;
}
.sub {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 14px;
}
.bar {
  display: grid;
  grid-template-columns: 160px 1fr 140px auto auto;
  gap: 10px;
  align-items: center;
}
</style>
