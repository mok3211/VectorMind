<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NButton, NCard, NSelect, NSpin, NText, NInput, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

type PromptItem = { agent: string; name: string; versions: string[] }

const message = useMessage()
const loading = ref(false)
const list = ref<PromptItem[]>([])

const agent = ref<string | null>(null)
const version = ref<string | null>(null)

const system = ref('')
const user = ref('')

const agentOptions = computed(() => list.value.map((i) => ({ label: i.name, value: i.agent })))
const versionOptions = computed(() => {
  const it = list.value.find((x) => x.agent === agent.value)
  return (it?.versions ?? []).map((v) => ({ label: v, value: v }))
})

const canLoad = computed(() => !!agent.value && !!version.value)

async function fetchList() {
  const { data } = await api.get('/api/prompts')
  list.value = data.items
  agent.value = data.items?.[0]?.agent ?? null
  version.value = data.items?.[0]?.versions?.[0] ?? 'v1'
}

async function load() {
  if (!canLoad.value) return
  loading.value = true
  try {
    const { data } = await api.get(`/api/prompts/${agent.value}/${version.value}`)
    system.value = data.system
    user.value = data.user
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!canLoad.value) return
  loading.value = true
  try {
    await api.put(`/api/prompts/${agent.value}/${version.value}`, {
      system: system.value,
      user: user.value
    })
    message.success('已保存')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchList()
  await load()
})
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between; gap: 12px">
        <span>Prompt 管理</span>
        <div style="display:flex; gap: 10px; align-items:center">
          <NSelect v-model:value="agent" :options="agentOptions" style="width: 220px" @update:value="load" />
          <NSelect
            v-model:value="version"
            :options="versionOptions"
            style="width: 120px"
            @update:value="load"
          />
          <NButton secondary :disabled="!canLoad" :loading="loading" @click="load">刷新</NButton>
          <NButton type="primary" :disabled="!canLoad" :loading="loading" @click="save">保存</NButton>
        </div>
      </div>
    </template>

    <NText depth="3" style="display:block; margin-bottom: 10px">
      这里编辑的是各 agent 的 <code>prompts/{{ version || 'v1' }}/system.jinja</code> 与
      <code>user.jinja</code> 文件。建议按版本迭代（例如 v1 → v2）。
    </NText>

    <NSpin :show="loading">
      <div class="grid">
        <div class="box">
          <div class="title">system.jinja</div>
          <NInput v-model:value="system" type="textarea" :autosize="{ minRows: 14, maxRows: 28 }" />
        </div>
        <div class="box">
          <div class="title">user.jinja</div>
          <NInput v-model:value="user" type="textarea" :autosize="{ minRows: 14, maxRows: 28 }" />
        </div>
      </div>
    </NSpin>
  </NCard>
</template>

<style scoped>
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.box {
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 10px;
}
.title {
  font-weight: 750;
  margin: 2px 0 8px;
}
@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>

