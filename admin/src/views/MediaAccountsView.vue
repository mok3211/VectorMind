<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NSelect,
  NTag,
  useMessage
} from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()

const items = ref<any[]>([])
const loading = ref(false)

const show = ref(false)
const platform = ref('xhs')
const nickname = ref<string | null>(null)
const notes = ref<string | null>(null)

async function reload() {
  loading.value = true
  try {
    const { data } = await api.get('/api/media-accounts')
    items.value = data.items
  } finally {
    loading.value = false
  }
}

onMounted(reload)

async function createOne() {
  const { data } = await api.post('/api/media-accounts', {
    platform: platform.value,
    nickname: nickname.value,
    notes: notes.value
  })
  message.success('已创建')
  show.value = false
  platform.value = 'xhs'
  nickname.value = null
  notes.value = null
  await reload()
  return data
}

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  {
    title: '平台',
    key: 'platform',
    width: 140,
    render(row: any) {
      return row.platform ? h('span', { style: 'font-weight:650' }, row.platform) : '-'
    }
  },
  { title: '昵称', key: 'nickname' },
  {
    title: '状态',
    key: 'status',
    width: 140,
    render(row: any) {
      const map: Record<string, any> = {
        connected: 'success',
        expired: 'warning',
        disconnected: 'default'
      }
      return h(
        NTag,
        { size: 'small', type: map[row.status] ?? 'default' },
        { default: () => row.status }
      )
    }
  },
  { title: '备注', key: 'notes' },
  { title: '更新时间', key: 'updated_at', width: 220 },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render(row: any) {
      return h('div', { style: 'display:flex; gap:8px' }, [
        h(
          NButton,
          {
            size: 'small',
            tertiary: true,
            onClick: () => connectAccount(row.id)
          },
          { default: () => '扫码连接' }
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            tertiary: true,
            onClick: () => quickPublish(row.id)
          },
          { default: () => '测试发布' }
        )
      ])
    }
  }
]

const platformOptions = [
  { label: '小红书 xhs', value: 'xhs' },
  { label: '抖音 douyin', value: 'douyin' }
]

async function connectAccount(accountId: number) {
  message.info('即将打开浏览器，请扫码登录')
  const { data } = await api.post(`/api/media-publish/accounts/${accountId}/connect`, {
    timeout_sec: 180,
    headless: false
  })
  if (data.ok) {
    message.success('连接成功')
  } else {
    message.warning(data.detail || '连接失败')
  }
  await reload()
}

async function quickPublish(accountId: number) {
  const { data } = await api.post(`/api/media-publish/accounts/${accountId}/publish`, {
    title: '自动发布测试',
    text: '这是一条来自 VectorMind 的自动发布测试文案。',
    tags: ['自动化', '测试'],
    dry_run: true
  })
  if (data.ok) {
    message.success(data.detail || '已打开发布页')
  } else {
    message.warning(data.detail || '发布失败')
  }
}
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between">
        <span>媒体账号</span>
        <NButton type="primary" @click="show = true">新增</NButton>
      </div>
    </template>

    <NDataTable :columns="columns" :data="items" :loading="loading" />
  </NCard>

  <NModal v-model:show="show" preset="card" title="新增媒体账号" class="modal">
    <NForm>
      <NFormItem label="平台">
        <NSelect v-model:value="platform" :options="platformOptions" />
      </NFormItem>
      <NFormItem label="昵称">
        <NInput v-model:value="nickname" placeholder="可选" />
      </NFormItem>
      <NFormItem label="备注">
        <NInput v-model:value="notes" placeholder="例如：用来发书单/旅游" />
      </NFormItem>
      <div style="display:flex; justify-content:flex-end; gap: 10px">
        <NButton secondary @click="show = false">取消</NButton>
        <NButton type="primary" @click="createOne">创建</NButton>
      </div>
    </NForm>
  </NModal>
</template>

<style scoped>
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
.modal {
  width: min(520px, 92vw);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(20, 20, 24, 0.85);
  backdrop-filter: blur(12px);
}
</style>
