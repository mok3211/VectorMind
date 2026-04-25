<script setup lang="ts">
import { computed, ref } from 'vue'
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
  NText
} from 'naive-ui'
import { api } from '@/lib/api'

type AgentKey = 'morning_radio' | 'book_recommendation' | 'travel_planner' | 'morning_history'

const agent = ref<AgentKey>('morning_radio')
const loading = ref(false)
const output = ref('')
const meta = ref<any>(null)

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

async function run() {
  loading.value = true
  output.value = ''
  meta.value = null
  try {
    const { data } = await api.post(endpoint.value, payload.value)
    output.value = data.text
    meta.value = data.meta
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

        <NForm>
          <NFormItem label="选择 Agent">
            <NSelect v-model:value="agent" :options="agentOptions" />
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
            <NButton type="primary" :loading="loading" @click="run">生成</NButton>
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

