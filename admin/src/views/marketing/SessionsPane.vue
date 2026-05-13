<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  useMessage
} from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()
const profiles = ref<any[]>([])
const sessions = ref<any[]>([])
const loading = ref(false)

const profileId = ref<number | null>(null)
const userAgent = ref<string | null>(null)
const sessionJson = ref<string>('{}')

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
    const [p, s] = await Promise.all([api.get('/api/marketing/profiles?limit=200'), api.get('/api/marketing/sessions?limit=200')])
    profiles.value = p.data.items
    sessions.value = s.data.items
    if (!profileId.value && profiles.value.length) profileId.value = profiles.value[0].id
  } finally {
    loading.value = false
  }
}

const profileOptions = computed(() =>
  profiles.value.map((p) => ({
    label: `${p.id} · ${p.platform} · ${p.nickname ?? p.sec_uid ?? '-'}`,
    value: p.id
  }))
)

async function importOne() {
  if (!profileId.value) return
  let obj: any = {}
  try {
    obj = JSON.parse(sessionJson.value || '{}')
  } catch {
    message.error('session_data 不是合法 JSON')
    return
  }
  await api.post('/api/marketing/sessions/import', {
    profile_id: profileId.value,
    user_agent: userAgent.value,
    session_data: obj
  })
  message.success('已导入（MarketingSession v1）')
  await reload()
}

async function validateOne(id: number) {
  await api.post(`/api/marketing/sessions/${id}/validate`)
  message.success('已校验（stub）')
  await reload()
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
      <NFormItem label="Profile">
        <NSelect v-model:value="profileId" :options="profileOptions" />
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
    <NDataTable :columns="columns" :data="sessions" :loading="loading" />
  </NCard>
</template>

<style scoped>
.sub {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
}
</style>
