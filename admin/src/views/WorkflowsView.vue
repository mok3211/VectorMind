<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NCard, NSelect, NText } from 'naive-ui'
import { api } from '@/lib/api'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'

type Workflow = {
  agent: string
  name: string
  nodes: Array<{ id: string; label: string; position: { x: number; y: number } }>
  edges: Array<{ id: string; source: string; target: string }>
}

const list = ref<Workflow[]>([])
const selected = ref<string | null>(null)

onMounted(async () => {
  const { data } = await api.get('/api/workflows')
  list.value = data.items
  selected.value = data.items?.[0]?.agent ?? null
})

const options = computed(() => list.value.map((w) => ({ label: w.name, value: w.agent })))
const current = computed(() => list.value.find((w) => w.agent === selected.value) ?? null)

const nodes = computed(() =>
  (current.value?.nodes ?? []).map((n) => ({
    id: n.id,
    position: n.position,
    data: { label: n.label },
    type: 'default',
    draggable: false
  }))
)

const edges = computed(() => (current.value?.edges ?? []).map((e) => ({ id: e.id, source: e.source, target: e.target })))
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>
      <div style="display:flex; align-items:center; justify-content:space-between; gap: 12px">
        <span>工作流可视化</span>
        <NSelect v-model:value="selected" :options="options" style="width: 220px" />
      </div>
    </template>
    <NText depth="3" style="display:block; margin-bottom: 10px">
      每个 Agent 的关键节点（Prompt → LLM → 输出 → 素材/发布预留）。后续接入生图/生视频后，这里会直观看到节点与状态。
    </NText>

    <div class="flow">
      <VueFlow :nodes="nodes" :edges="edges" :fit-view="true">
        <Background pattern-color="rgba(255,255,255,0.08)" :gap="18" />
        <Controls />
      </VueFlow>
    </div>
  </NCard>
</template>

<style scoped>
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
.flow {
  height: 560px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.18);
}
:deep(.vue-flow__node-default) {
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.04));
  color: rgba(255, 255, 255, 0.92);
  font-weight: 650;
  letter-spacing: 0.2px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
}
:deep(.vue-flow__edge-path) {
  stroke: rgba(255, 255, 255, 0.28);
}
</style>

