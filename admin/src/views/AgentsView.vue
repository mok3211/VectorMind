<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NForm,
  NFormItem,
  NGrid,
  NGridItem,
  NInput,
  NInputNumber,
  NSelect,
  NTag,
  NText,
  useMessage
} from 'naive-ui'
import { api } from '@/lib/api'

type AgentKey = 'morning_radio' | 'book_recommendation' | 'travel_planner' | 'morning_history'

const agent = ref<AgentKey>('morning_radio')
const loading = ref(false)
const output = ref('')
const meta = ref<any>(null)
const message = useMessage()

type Provider = 'nvidia_nim' | 'openai' | 'gemini' | 'deepseek'
const modelMode = ref<'default' | 'server' | 'local'>('default')
const serverConfigs = ref<any[]>([])
const serverConfigId = ref<number | null>(null)
const localConfigId = ref<string | null>(null)
const modelOverride = ref<string | null>(null)

const localStorageKey = 'llm_local_configs_v1'
const localConfigs = ref<any[]>([])

function loadLocalConfigs() {
  try {
    const raw = localStorage.getItem(localStorageKey)
    const data = raw ? JSON.parse(raw) : []
    localConfigs.value = Array.isArray(data) ? data : []
  } catch {
    localConfigs.value = []
  }
}

async function loadServerConfigs() {
  try {
    const { data } = await api.get('/api/llm/configs')
    serverConfigs.value = data.items ?? []
  } catch {
    serverConfigs.value = []
  }
}

async function loadDefault() {
  try {
    const { data } = await api.get('/api/llm/default')
    const d = data.item ?? {}
    serverConfigId.value = d.config_id ?? null
    modelOverride.value = d.model ?? null
  } catch {
    // ignore
  }
}

onMounted(async () => {
  loadLocalConfigs()
  await loadServerConfigs()
  await loadDefault()
})

// inputs
const topic = ref<string | null>(null)
const audience = ref<string | null>(null)

const theme = ref<string | null>(null)
const level = ref<string | null>(null)

const destination = ref('杭州')
const days = ref(3)
const budget = ref<string | null>('中等')
const preferences = ref<string | null>('人文+美食')

const agentOptions = [
  { label: '早安电台', value: 'morning_radio' },
  { label: '书单推荐', value: 'book_recommendation' },
  { label: '旅游规划', value: 'travel_planner' },
  { label: '早安历史', value: 'morning_history' }
]

const serverOptions = computed(() =>
  serverConfigs.value.map((x: any) => ({
    label: `${x.name} · ${x.provider}`,
    value: x.id
  }))
)

const localOptions = computed(() =>
  localConfigs.value.map((x: any) => ({
    label: `${x.name} · ${x.provider}`,
    value: x.id
  }))
)

const endpoint = computed(() => {
  switch (agent.value) {
    case 'morning_radio':
      return '/morning-radio/generate'
    case 'book_recommendation':
      return '/book-recommendation/generate'
    case 'travel_planner':
      return '/travel-planner/generate'
    case 'morning_history':
      return '/morning-history/generate'
  }
})

const payload = computed(() => {
  switch (agent.value) {
    case 'morning_radio':
      return { topic: topic.value, audience: audience.value }
    case 'book_recommendation':
      return { theme: theme.value, level: level.value }
    case 'travel_planner':
      return { destination: destination.value, days: days.value, budget: budget.value, preferences: preferences.value }
    case 'morning_history':
      return {}
  }
})

const llm = computed(() => {
  if (modelMode.value === 'default') {
    return { mode: 'default', model: modelOverride.value || null }
  }
  if (modelMode.value === 'server') {
    return {
      mode: 'server',
      config_id: serverConfigId.value,
      model: modelOverride.value || null
    }
  }
  const cfg = localConfigs.value.find((x: any) => x.id === localConfigId.value) ?? null
  return {
    mode: 'local',
    provider: (cfg?.provider as Provider) ?? null,
    api_key: cfg?.api_key ?? null,
    api_base: cfg?.api_base ?? null,
    model: modelOverride.value || null
  }
})

async function run() {
  loading.value = true
  output.value = `准备调用：${endpoint.value}\n`
  meta.value = null
  try {
    // 便于定位：在浏览器控制台也打印一次
    // eslint-disable-next-line no-console
    console.log('[AgentsView] POST', endpoint.value, payload.value, llm.value)
    const { data } = await api.post(endpoint.value, { ...payload.value, llm: llm.value }, { timeout: 300_000 })
    output.value = data.text
    meta.value = data.meta
  } catch (e: any) {
    const detail = e?.response?.data?.detail ?? e?.message ?? '生成失败'
    message.error(String(detail))
    output.value = `${output.value}\n调用失败：${String(detail)}`
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <NGrid :cols="2" x-gap="14" y-gap="14">
    <NGridItem>
      <NCard class="panel" size="small">
        <template #header>运行 Agent</template>

        <!-- 防止表单默认 submit 导致页面刷新、请求未发出 -->
        <NForm @submit.prevent="run">
          <NFormItem label="选择 Agent">
            <NSelect v-model:value="agent" :options="agentOptions" />
          </NFormItem>

          <NFormItem label="模型/Key">
            <div style="display:flex; flex-direction:column; gap:10px; width: 100%">
              <div style="display:grid; grid-template-columns: 160px 1fr; gap: 10px; width: 100%">
                <NSelect
                  v-model:value="modelMode"
                  :options="[
                    { label: '使用默认', value: 'default' },
                    { label: '服务器配置', value: 'server' },
                    { label: '本地配置', value: 'local' }
                  ]"
                />
                <template v-if="modelMode === 'server'">
                  <NSelect v-model:value="serverConfigId" :options="serverOptions" placeholder="选择服务器配置" />
                </template>
                <template v-else-if="modelMode === 'local'">
                  <NSelect v-model:value="localConfigId" :options="localOptions" placeholder="选择本地配置" />
                </template>
                <template v-else>
                  <NInput value="全局默认（后端决定 provider/model）" disabled />
                </template>
              </div>
              <NInput
                v-model:value="modelOverride"
                placeholder="model（可空）：NVIDIA 用 meta/llama-3.1-70b-instruct；OpenAI 用 openai/gpt-4o-mini；Gemini 用 gemini/gemini-1.5-flash；DeepSeek 用 deepseek/deepseek-chat"
              />
            </div>
          </NFormItem>

          <template v-if="agent === 'morning_radio'">
            <NFormItem label="主题">
              <NInput v-model:value="topic" placeholder="给忙碌的人一个温柔的早晨" />
            </NFormItem>
            <NFormItem label="受众">
              <NInput v-model:value="audience" placeholder="上班族/学生" />
            </NFormItem>
          </template>

          <template v-else-if="agent === 'book_recommendation'">
            <NFormItem label="领域">
              <NInput v-model:value="theme" placeholder="个人成长与效率" />
            </NFormItem>
            <NFormItem label="读者水平">
              <NInput v-model:value="level" placeholder="入门/进阶" />
            </NFormItem>
          </template>

          <template v-else-if="agent === 'travel_planner'">
            <NFormItem label="目的地">
              <NInput v-model:value="destination" />
            </NFormItem>
            <NFormItem label="天数">
              <NInputNumber v-model:value="days" :min="1" :max="30" style="width: 100%" />
            </NFormItem>
            <NFormItem label="预算">
              <NInput v-model:value="budget" placeholder="低/中等/高" />
            </NFormItem>
            <NFormItem label="偏好">
              <NInput v-model:value="preferences" placeholder="人文+美食/亲子/徒步..." />
            </NFormItem>
          </template>

          <template v-else>
            <NText depth="3">早安历史会自动使用今天日期生成。</NText>
          </template>

          <div style="display:flex; justify-content:flex-end; margin-top: 10px">
            <NButton type="primary" :loading="loading" attr-type="button" @click="run">生成</NButton>
          </div>
        </NForm>
      </NCard>
    </NGridItem>

    <NGridItem>
      <NCard class="panel" size="small">
        <template #header>
          <div style="display:flex; align-items:center; justify-content:space-between; gap: 10px">
            <span>输出</span>
            <NTag v-if="meta?.model" size="small" type="success">{{ meta.model }}</NTag>
          </div>
        </template>

        <pre class="out">{{ output || '（等待生成）' }}</pre>
      </NCard>
    </NGridItem>
  </NGrid>
</template>

<style scoped>
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
.out {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.88);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: 12.5px;
  padding: 10px 10px;
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.08);
  min-height: 360px;
}
</style>
