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
    const { data } = await api.post('/api/marketing/search/creators', {
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

async function addCompetitor(row: any) {
  try {
    await api.post('/api/marketing/profiles', {
      platform: row.platform,
      profile_type: 'competitor',
      sec_uid: row.sec_uid || row.platform_user_id || null,
      nickname: row.nickname || null,
      user_link: row.user_link || null
    })
    message.success('已添加为竞品/监控账号')
  } catch (e: any) {
    const detail = e?.response?.data?.detail ?? e?.message ?? '添加失败'
    message.error(String(detail))
  }
}

function openUrl(row: any) {
  const u = row.user_link || ''
  if (u) window.open(u, '_blank')
}

onMounted(() => {})

const columns = [
  { title: '平台', key: 'platform', width: 90, render: (r: any) => h(NTag, { size: 'small' }, { default: () => r.platform }) },
  { title: '昵称', key: 'nickname', width: 240, ellipsis: { tooltip: true } },
  { title: 'user_id', key: 'platform_user_id', width: 260 },
  { title: '主页', key: 'user_link', minWidth: 360, ellipsis: { tooltip: true } },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right' as const,
    render(row: any) {
      return h('div', { style: 'display:flex; gap:8px' }, [
        h(NButton, { size: 'small', secondary: true, onClick: () => openUrl(row) }, { default: () => '打开' }),
        h(NButton, { size: 'small', tertiary: true, onClick: () => addCompetitor(row) }, { default: () => '加入监控' })
      ])
    }
  }
]
</script>

<template>
  <div class="wrap">
    <NCard size="small" class="sub">
      <template #header>达人搜索</template>
      <div class="bar">
        <NSelect
          v-model:value="platform"
          style="width: 160px"
          :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]"
        />
        <NInput v-model:value="keyword" placeholder="输入关键词（会从视频搜索结果里提取达人）" />
        <NInputNumber v-model:value="page" :min="1" :max="10" style="width: 140px" />
        <NButton type="primary" :loading="loading" @click="search">搜索</NButton>
        <NButton secondary @click="router.push('/marketing/sessions')">去扫码登录</NButton>
      </div>
    </NCard>

    <NCard size="small" class="sub">
      <template #header>搜索结果</template>
      <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="1260" />
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
