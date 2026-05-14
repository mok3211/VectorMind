<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NDivider,
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

type Provider = 'nvidia_nim' | 'openai' | 'gemini' | 'deepseek'

const providerOptions = [
  { label: 'NVIDIA NIM', value: 'nvidia_nim' },
  { label: 'OpenAI', value: 'openai' },
  { label: 'Gemini', value: 'gemini' },
  { label: 'DeepSeek', value: 'deepseek' }
]

const loading = ref(false)
const serverItems = ref<any[]>([])
const localItems = ref<any[]>([])

const show = ref(false)
const editing = ref<{ scope: 'server' | 'local'; id?: number; idx?: number } | null>(null)

const scope = ref<'server' | 'local'>('server')
const name = ref('')
const provider = ref<Provider>('nvidia_nim')
const apiKey = ref('')
const apiBase = ref<string | null>(null)

const defaultConfigId = ref<number | null>(null)
const defaultModel = ref<string | null>(null)

const localStorageKey = 'llm_local_configs_v1'

function loadLocal() {
  try {
    const raw = localStorage.getItem(localStorageKey)
    const data = raw ? JSON.parse(raw) : []
    localItems.value = Array.isArray(data) ? data : []
  } catch {
    localItems.value = []
  }
}

function saveLocal() {
  localStorage.setItem(localStorageKey, JSON.stringify(localItems.value))
}

async function reloadServer() {
  const { data } = await api.get('/api/llm/configs')
  serverItems.value = data.items ?? []
}

async function reloadDefault() {
  const { data } = await api.get('/api/llm/default')
  defaultConfigId.value = data.item?.config_id ?? null
  defaultModel.value = data.item?.model ?? null
}

async function reloadAll() {
  loading.value = true
  try {
    loadLocal()
    await reloadServer()
    await reloadDefault()
  } finally {
    loading.value = false
  }
}

onMounted(reloadAll)

function openCreate(s: 'server' | 'local') {
  scope.value = s
  editing.value = { scope: s }
  name.value = ''
  provider.value = 'nvidia_nim'
  apiKey.value = ''
  apiBase.value = null
  show.value = true
}

function openEditServer(row: any) {
  scope.value = 'server'
  editing.value = { scope: 'server', id: row.id }
  name.value = row.name ?? ''
  provider.value = row.provider ?? 'nvidia_nim'
  apiKey.value = ''
  apiBase.value = row.api_base ?? null
  show.value = true
}

function openEditLocal(row: any, idx: number) {
  scope.value = 'local'
  editing.value = { scope: 'local', idx }
  name.value = row.name ?? ''
  provider.value = row.provider ?? 'nvidia_nim'
  apiKey.value = row.api_key ?? ''
  apiBase.value = row.api_base ?? null
  show.value = true
}

async function save() {
  if (!name.value.trim()) return message.error('名称不能为空')
  if (!provider.value) return message.error('provider 不能为空')

  if (scope.value === 'server') {
    if (!editing.value?.id) {
      if (!apiKey.value.trim()) return message.error('Key 不能为空')
      await api.post('/api/llm/configs', {
        name: name.value,
        provider: provider.value,
        api_key: apiKey.value,
        api_base: apiBase.value
      })
      message.success('已保存到服务器')
    } else {
      await api.put(`/api/llm/configs/${editing.value.id}`, {
        name: name.value,
        api_key: apiKey.value || null,
        api_base: apiBase.value
      })
      message.success('已更新服务器配置')
    }
    await reloadServer()
  } else {
    const item = {
      id: crypto.randomUUID(),
      name: name.value,
      provider: provider.value,
      api_key: apiKey.value,
      api_base: apiBase.value,
      updated_at: new Date().toISOString()
    }
    if (editing.value?.idx != null) {
      localItems.value.splice(editing.value.idx, 1, item)
    } else {
      localItems.value.unshift(item)
    }
    saveLocal()
    message.success('已保存到浏览器')
  }
  show.value = false
}

async function removeServer(row: any) {
  await api.delete(`/api/llm/configs/${row.id}`)
  message.success('已删除')
  await reloadServer()
}

function removeLocal(idx: number) {
  localItems.value.splice(idx, 1)
  saveLocal()
  message.success('已删除')
}

const defaultOptions = computed(() => [
  { label: '不设置（每次运行可选）', value: null },
  ...serverItems.value.map((x: any) => ({
    label: `${x.name} · ${x.provider}`,
    value: x.id
  }))
])

async function saveDefault() {
  await api.put('/api/llm/default', {
    config_id: defaultConfigId.value,
    model: defaultModel.value
  })
  message.success('默认已保存')
}

const serverColumns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '名称', key: 'name', width: 220 },
  {
    title: 'Provider',
    key: 'provider',
    width: 140,
    render: (row: any) => h(NTag, { size: 'small', type: 'success' }, { default: () => row.provider })
  },
  { title: 'Key', key: 'key_mask', width: 200 },
  { title: 'API Base', key: 'api_base' },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: (row: any) =>
      h('div', { style: 'display:flex; gap:8px' }, [
        h(
          NButton,
          { size: 'small', secondary: true, onClick: () => openEditServer(row) },
          { default: () => '编辑' }
        ),
        h(NButton, { size: 'small', tertiary: true, onClick: () => removeServer(row) }, { default: () => '删除' })
      ])
  }
]

const localColumns = [
  { title: '名称', key: 'name', width: 220 },
  {
    title: 'Provider',
    key: 'provider',
    width: 140,
    render: (row: any) => h(NTag, { size: 'small', type: 'warning' }, { default: () => row.provider })
  },
  {
    title: 'Key',
    key: 'api_key',
    width: 220,
    render: (row: any) => String(row.api_key || '').slice(0, 4) + '****' + String(row.api_key || '').slice(-4)
  },
  { title: 'API Base', key: 'api_base' },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render: (_row: any, idx: number) =>
      h('div', { style: 'display:flex; gap:8px' }, [
        h(
          NButton,
          { size: 'small', secondary: true, onClick: () => openEditLocal(localItems.value[idx], idx) },
          { default: () => '编辑' }
        ),
        h(NButton, { size: 'small', tertiary: true, onClick: () => removeLocal(idx) }, { default: () => '删除' })
      ])
  }
]
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between; gap: 10px">
        <span>模型与 Key</span>
        <div style="display:flex; gap: 10px">
          <NButton secondary @click="openCreate('local')">新增本地配置</NButton>
          <NButton type="primary" @click="openCreate('server')">新增服务器配置</NButton>
        </div>
      </div>
    </template>

    <div style="display:grid; gap: 12px">
      <NCard size="small" class="sub">
        <template #header>默认模型（全局）</template>
        <div style="display:grid; grid-template-columns: 1fr 1fr auto; gap: 12px; align-items:end">
          <div>
            <div style="font-size:12px; color: var(--muted); margin-bottom: 6px">默认 Provider 配置（服务器）</div>
            <NSelect v-model:value="defaultConfigId" :options="defaultOptions" clearable />
          </div>
          <div>
            <div style="font-size:12px; color: var(--muted); margin-bottom: 6px">默认 Model（可空）</div>
            <NInput v-model:value="defaultModel" placeholder="例如：meta/llama-3.1-70b-instruct 或 openai/gpt-4o-mini" />
          </div>
          <NButton type="primary" @click="saveDefault">保存默认</NButton>
        </div>
      </NCard>

      <NDivider />

      <div style="display:grid; grid-template-columns: 1fr; gap: 12px">
        <NCard size="small" class="sub">
          <template #header>服务器配置（共享）</template>
          <NDataTable :columns="serverColumns" :data="serverItems" :loading="loading" />
        </NCard>

        <NCard size="small" class="sub">
          <template #header>本地配置（仅当前浏览器）</template>
          <NDataTable :columns="localColumns" :data="localItems" :loading="loading" />
        </NCard>
      </div>
    </div>
  </NCard>

  <NModal v-model:show="show" preset="card" title="配置" class="modal">
    <NForm>
      <NFormItem label="存储位置">
        <NSelect v-model:value="scope" :options="[{ label: '服务器', value: 'server' }, { label: '本地浏览器', value: 'local' }]" />
      </NFormItem>
      <NFormItem label="名称">
        <NInput v-model:value="name" placeholder="例如：NVIDIA-生产 / OpenAI-个人" />
      </NFormItem>
      <NFormItem label="Provider">
        <NSelect v-model:value="provider" :options="providerOptions" />
      </NFormItem>
      <NFormItem label="API Key">
        <NInput v-model:value="apiKey" type="password" placeholder="仅保存一次；服务器编辑不填则不改" />
      </NFormItem>
      <NFormItem label="API Base（可选）">
        <NInput v-model:value="apiBase" placeholder="可留空" />
      </NFormItem>
      <div style="display:flex; justify-content:flex-end; gap:10px">
        <NButton secondary @click="show = false">取消</NButton>
        <NButton type="primary" @click="save">保存</NButton>
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
.sub {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.12);
}
.modal {
  width: min(760px, 94vw);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(20, 20, 24, 0.85);
  backdrop-filter: blur(12px);
}
</style>
