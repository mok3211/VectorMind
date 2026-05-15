<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NPopconfirm,
  NModal,
  NSelect,
  NTag,
  useMessage
} from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()

const items = ref<any[]>([])
const loading = ref(false)
const loginPolling = ref(false)
const creating = ref(false)

const filterPlatform = ref<string | null>(null)
const filterStatus = ref<string | null>(null)

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

const show = ref(false)
const platform = ref('xhs')
const nickname = ref<string | null>(null)
const notes = ref<string | null>(null)

async function reload() {
  loading.value = true
  try {
    const qs = new URLSearchParams()
    qs.set('page', String(pagination.page))
    qs.set('page_size', String(pagination.pageSize))
    if (filterPlatform.value) qs.set('platform', filterPlatform.value)
    if (filterStatus.value) qs.set('status', filterStatus.value)
    const { data } = await api.get(`/api/media-accounts?${qs.toString()}`)
    items.value = data.items
    pagination.itemCount = data.total ?? data.items?.length ?? 0
  } finally {
    loading.value = false
  }
}

onMounted(reload)

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function createOne() {
  creating.value = true
  try {
    const { data } = await api.post('/api/media-accounts', {
      platform: platform.value,
      nickname: nickname.value,
      notes: notes.value,
      auto_login: true
    })
    message.success('已创建，已打开浏览器窗口，请扫码登录')
    show.value = false
    platform.value = 'xhs'
    nickname.value = null
    notes.value = null

    const runId = data?.login_run?.id
    if (runId) {
      loginPolling.value = true
      try {
        while (true) {
          const r = await api.get(`/api/marketing/qr-login/${runId}`)
          const run = r.data.run
          if (run.status !== 'running') {
            if (run.status === 'success') message.success('登录成功')
            else message.error(run.error || '登录失败')
            break
          }
          await sleep(2000)
        }
      } finally {
        loginPolling.value = false
      }
    }

    await reload()
    return data
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '创建失败'
    message.error(String(detail))
    return null
  } finally {
    creating.value = false
  }
}

async function startLogin(row: any) {
  loginPolling.value = true
  try {
    const { data } = await api.post(`/api/media-accounts/${row.id}/login`)
    const runId = data?.run?.id
    if (!runId) return
    message.info('已打开浏览器窗口，请扫码登录')
    while (true) {
      const r = await api.get(`/api/marketing/qr-login/${runId}`)
      const run = r.data.run
      if (run.status !== 'running') {
        if (run.status === 'success') message.success('登录成功')
        else message.error(run.error || '登录失败')
        break
      }
      await sleep(2000)
    }
    await reload()
  } finally {
    loginPolling.value = false
  }
}

async function deleteOne(row: any) {
  await api.delete(`/api/media-accounts/${row.id}`)
  message.success('已删除')
  await reload()
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
  { title: '昵称', key: 'nickname', width: 240, ellipsis: { tooltip: true } },
  {
    title: '状态',
    key: 'status',
    width: 140,
    render(row: any) {
      const map: Record<string, any> = {
        connected: 'success',
        expired: 'warning',
        disconnected: 'default',
        connecting: 'info'
      }
      return h(
        NTag,
        { size: 'small', type: map[row.status] ?? 'default' },
        { default: () => row.status }
      )
    }
  },
  { title: '备注', key: 'notes', width: 260, ellipsis: { tooltip: true } },
  { title: '更新时间', key: 'updated_at', width: 220 },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    fixed: 'right' as const,
    render(row: any) {
      return h('div', { style: 'display:flex; gap:8px' }, [
        h(
          NButton,
          { size: 'small', secondary: true, loading: loginPolling.value, onClick: () => startLogin(row) },
          { default: () => '登录' }
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => deleteOne(row) },
          {
            trigger: () => h(NButton, { size: 'small', tertiary: true }, { default: () => '删除' }),
            default: () => '确定删除这个账号吗？'
          }
        )
      ])
    }
  }
]

const platformOptions = [
  { label: '小红书 xhs', value: 'xhs' },
  { label: '抖音 douyin', value: 'douyin' }
]
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between">
        <span>媒体账号</span>
        <div style="display:flex; gap:10px">
          <NButton secondary :loading="loading" @click="reload">刷新</NButton>
          <NButton type="primary" @click="show = true">新增</NButton>
        </div>
      </div>
    </template>

    <div style="display:flex; gap:10px; align-items:center; margin-bottom: 10px">
      <NSelect
        v-model:value="filterPlatform"
        clearable
        placeholder="平台"
        style="width: 160px"
        :options="platformOptions"
      />
      <NSelect
        v-model:value="filterStatus"
        clearable
        placeholder="状态"
        style="width: 160px"
        :options="[
          { label: 'connected', value: 'connected' },
          { label: 'expired', value: 'expired' },
          { label: 'disconnected', value: 'disconnected' }
        ]"
      />
      <div style="flex: 1" />
      <NButton secondary :loading="loading" @click="reload">查询</NButton>
    </div>

    <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="1180" remote :pagination="pagination" />
  </NCard>

  <NModal v-model:show="show" preset="card" title="新增媒体账号" class="modal">
    <NForm size="small" label-width="70">
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
        <NButton secondary :disabled="creating || loginPolling" @click="show = false">取消</NButton>
        <NButton type="primary" :loading="creating" :disabled="loginPolling" @click="createOne">创建</NButton>
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
  width: min(460px, 92vw);
  max-height: 82vh;
  overflow: auto;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(20, 20, 24, 0.85);
  backdrop-filter: blur(12px);
}
.modal :deep(.n-card-header) {
  padding: 14px 16px;
}
.modal :deep(.n-card__content) {
  padding: 12px 16px 16px;
}
.modal :deep(.n-form-item) {
  margin-bottom: 10px;
}
</style>
