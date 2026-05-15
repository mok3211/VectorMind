<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NCard, NDataTable, NInput, NModal, NTag, NText } from 'naive-ui'
import { api } from '@/lib/api'

const items = ref<any[]>([])
const loading = ref(false)

const show = ref(false)
const current = ref<any | null>(null)

const agent = ref<string | null>(null)

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

async function reload() {
  loading.value = true
  try {
    const qs = new URLSearchParams()
    qs.set('page', String(pagination.page))
    qs.set('page_size', String(pagination.pageSize))
    if (agent.value?.trim()) qs.set('agent', agent.value.trim())
    const { data } = await api.get(`/api/runs?${qs.toString()}`)
    items.value = data.items
    pagination.itemCount = data.total ?? data.items?.length ?? 0
  } finally {
    loading.value = false
  }
}

onMounted(reload)

async function openRun(id: number) {
  const { data } = await api.get(`/api/runs/${id}`)
  current.value = data.item
  show.value = true
}

function prettyJson(s: string | null | undefined) {
  if (!s) return ''
  try {
    return JSON.stringify(JSON.parse(s), null, 2)
  } catch {
    return s
  }
}

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  {
    title: 'Agent',
    key: 'agent',
    width: 170,
    render(row: any) {
      return row.agent ? h(NTag, { size: 'small' }, { default: () => row.agent }) : '-'
    }
  },
  { title: 'Model', key: 'model', width: 220, ellipsis: { tooltip: true } },
  { title: 'Prompt', key: 'prompt_version', width: 120 },
  { title: 'Time', key: 'created_at' },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render(row: any) {
      return h(
        NButton,
        { size: 'small', secondary: true, onClick: () => openRun(row.id) },
        { default: () => '查看' }
      )
    }
  }
]
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>生成记录</template>
    <NText depth="3" style="display:block; margin-bottom: 10px">
      这里显示最近 50 条生成记录（用于复盘与迭代 prompt）。
    </NText>

    <div style="display:flex; gap:10px; align-items:center; margin-bottom: 10px">
      <NInput v-model:value="agent" placeholder="Agent 过滤（可选）" style="width: 260px" />
      <div style="flex: 1" />
      <NButton secondary :loading="loading" @click="reload">查询</NButton>
    </div>

    <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="920" remote :pagination="pagination" />
  </NCard>

  <NModal v-model:show="show" preset="card" title="运行详情" class="modal">
    <div v-if="!current">
      <NText depth="3">加载中...</NText>
    </div>
    <div v-else class="detail">
      <div class="row">
        <div class="k">Agent</div>
        <div class="v">{{ current.agent }}</div>
      </div>
      <div class="row">
        <div class="k">Model</div>
        <div class="v">{{ current.model ?? '-' }}</div>
      </div>
      <div class="row">
        <div class="k">Prompt</div>
        <div class="v">{{ current.prompt_version ?? '-' }}</div>
      </div>

      <div class="block">
        <div class="h">输入 input_json</div>
        <pre class="pre">{{ prettyJson(current.input_json) }}</pre>
      </div>
      <div class="block">
        <div class="h">输出 output_text</div>
        <pre class="pre">{{ current.output_text }}</pre>
      </div>
      <div class="block">
        <div class="h">步骤 steps_json</div>
        <pre class="pre">{{ prettyJson(current.steps_json) }}</pre>
      </div>
      <div class="block">
        <div class="h">素材 assets_json（预留）</div>
        <pre class="pre">{{ prettyJson(current.assets_json) }}</pre>
      </div>
    </div>
  </NModal>
</template>

<style scoped>
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
.modal {
  width: min(980px, 96vw);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(20, 20, 24, 0.85);
  backdrop-filter: blur(12px);
}
.detail {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.row {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 12px;
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.k {
  color: var(--muted);
  font-size: 12px;
}
.v {
  font-weight: 650;
}
.block {
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 10px;
}
.h {
  font-weight: 760;
  margin-bottom: 8px;
}
.pre {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New',
    monospace;
  font-size: 12.5px;
  color: rgba(255, 255, 255, 0.88);
}
</style>
