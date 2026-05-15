<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NText,
  useMessage
} from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()
const accounts = ref<any[]>([])
const sessions = ref<any[]>([])
const loading = ref(false)

const accountId = ref<number | null>(null)
const userAgent = ref<string | null>(null)
const sessionJson = ref<string>('{}')
const qrRun = ref<any | null>(null)
const qrPolling = ref(false)

const status = ref<string | null>(null)

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

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function fillTemplateXhs() {
  sessionJson.value = JSON.stringify(
    {
      version: 1,
      platform: 'xhs',
      auth: { cookies: [{ name: 'a1', value: 'xxx', domain: '.xiaohongshu.com', path: '/' }] },
      client: { user_agent: userAgent.value ?? 'Mozilla/5.0 ...' },
      device: { device_info: {} },
      verify: {},
      proxy: { enabled: false, url: '' },
      storage: { local_storage: {}, session_storage: {} },
      notes: ''
    },
    null,
    2
  )
}

function fillTemplateDouyin() {
  sessionJson.value = JSON.stringify(
    {
      version: 1,
      platform: 'douyin',
      auth: { cookies: [{ name: 'ttwid', value: 'xxx', domain: '.douyin.com', path: '/' }] },
      client: { user_agent: userAgent.value ?? 'Mozilla/5.0 ...', accept_language: 'zh-CN,zh;q=0.9' },
      device: { device_info: { browser_name: 'Chrome', os_name: 'Mac OS', screen_width: 1600 } },
      verify: { msToken: '', verifyFp: '', fp: '', webid: '' },
      proxy: { enabled: false, url: '' },
      storage: { local_storage: {}, session_storage: {} },
      notes: ''
    },
    null,
    2
  )
}

async function reload() {
  loading.value = true
  try {
    const qs = new URLSearchParams()
    qs.set('page', String(pagination.page))
    qs.set('page_size', String(pagination.pageSize))
    if (status.value) qs.set('status', status.value)
    const [a, s] = await Promise.all([api.get('/api/media-accounts'), api.get(`/api/marketing/sessions?${qs.toString()}`)])
    accounts.value = a.data.items
    sessions.value = s.data.items
    pagination.itemCount = s.data.total ?? s.data.items?.length ?? 0
    if (!accountId.value && accounts.value.length) accountId.value = accounts.value[0].id
  } finally {
    loading.value = false
  }
}

const accountOptions = computed(() =>
  accounts.value.map((a) => ({
    label: `${a.id} · ${a.platform} · ${a.nickname ?? '-'}`,
    value: a.id
  }))
)

async function importOne() {
  const acc = accounts.value.find((x) => x.id === accountId.value)
  const pid = acc?.profile_id
  if (!pid) {
    message.error('请先创建媒体账号，再扫码生成会话')
    return
  }
  let obj: any = {}
  try {
    obj = JSON.parse(sessionJson.value || '{}')
  } catch {
    message.error('session_data 不是合法 JSON')
    return
  }
  await api.post('/api/marketing/sessions/import', {
    profile_id: pid,
    user_agent: userAgent.value,
    session_data: obj
  })
  message.success('已导入（MarketingSession v1）')
  await reload()
}

async function validateOne(id: number) {
  await api.post(`/api/marketing/sessions/${id}/validate`)
  message.success('已校验')
  await reload()
}

async function startQrLogin() {
  const acc = accounts.value.find((x) => x.id === accountId.value)
  const pid = acc?.profile_id
  if (!pid) {
    message.error('请先创建媒体账号')
    return
  }
  qrPolling.value = true
  qrRun.value = null
  try {
    const { data } = await api.post('/api/marketing/qr-login/start', { profile_id: pid, timeout_sec: 300 })
    qrRun.value = data.run
    message.info('已打开浏览器窗口，请在弹出的窗口里扫码登录')
    while (true) {
      const r = await api.get(`/api/marketing/qr-login/${qrRun.value.id}`)
      qrRun.value = r.data.run
      if (qrRun.value.status !== 'running') break
      await sleep(2000)
    }
    if (qrRun.value.status === 'success') {
      message.success('登录成功，已生成会话')
    } else {
      message.error(qrRun.value.error || '登录失败')
    }
    await reload()
  } finally {
    qrPolling.value = false
  }
}

onMounted(reload)

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: 'profile_id', key: 'profile_id', width: 100 },
  { title: '状态', key: 'status', width: 120 },
  { title: '更新时间', key: 'updated_at', width: 220 },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    fixed: 'right' as const,
    render(row: any) {
      return h(
        NButton,
        { size: 'small', secondary: true, onClick: () => validateOne(row.id) },
        { default: () => '校验' }
      )
    }
  }
]
</script>

<template>
  <NCard size="small" class="sub">
    <template #header>导入会话（cookies/ua/device/verify 等）</template>
    <NForm>
      <NFormItem label="账号">
        <NSelect v-model:value="accountId" :options="accountOptions" />
      </NFormItem>
      <NFormItem label="本机扫码登录">
        <div style="display:flex; align-items:center; gap:10px; width:100%">
          <NButton type="primary" secondary :loading="qrPolling" @click="startQrLogin">打开浏览器扫码</NButton>
          <NText v-if="qrRun" depth="3">状态：{{ qrRun.status }}{{ qrRun.session_id ? ` · session ${qrRun.session_id}` : '' }}</NText>
        </div>
      </NFormItem>
      <NFormItem label="User-Agent">
        <NInput v-model:value="userAgent" placeholder="可选（建议填写）" />
      </NFormItem>
      <div style="display:flex; gap: 10px; justify-content:flex-end; margin-bottom: 10px">
        <NButton secondary @click="fillTemplateXhs">填充小红书模板</NButton>
        <NButton secondary @click="fillTemplateDouyin">填充抖音模板</NButton>
      </div>
      <NFormItem label="session_data (JSON)">
        <NInput v-model:value="sessionJson" type="textarea" :autosize="{ minRows: 8, maxRows: 18 }" />
      </NFormItem>
      <div style="display:flex; justify-content:flex-end; gap: 10px">
        <NButton secondary @click="reload">刷新</NButton>
        <NButton type="primary" @click="importOne">导入</NButton>
      </div>
    </NForm>
  </NCard>

  <NCard size="small" class="sub" style="margin-top: 12px">
    <template #header>会话列表</template>
    <div style="display:flex; gap:10px; align-items:center; margin-bottom: 10px">
      <NSelect
        v-model:value="status"
        clearable
        placeholder="状态"
        style="width: 160px"
        :options="[
          { label: 'valid', value: 'valid' },
          { label: 'expired', value: 'expired' },
          { label: 'invalid', value: 'invalid' }
        ]"
      />
      <div style="flex: 1" />
      <NButton secondary :loading="loading" @click="reload">查询</NButton>
    </div>

    <NDataTable :columns="columns" :data="sessions" :loading="loading" :scroll-x="820" remote :pagination="pagination" />
  </NCard>
</template>

<style scoped>
.sub {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
}
</style>
