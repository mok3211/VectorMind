<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { NCard, NGrid, NGridItem, NTag, NText } from 'naive-ui'
import { api } from '@/lib/api'

const stats = ref<{ runs: number; latestAgent?: string } | null>(null)
const recent = ref<any[]>([])

onMounted(async () => {
  try {
    const { data } = await api.get('/api/runs?limit=10')
    recent.value = data.items
    stats.value = { runs: data.items.length, latestAgent: data.items?.[0]?.agent }
  } catch {
    // ignore
  }
})

const cards = computed(() => [
  { title: 'Agent', desc: '4 个内容工作流', value: '4', tone: 'purple' },
  { title: '发布导出', desc: 'markdown / 小红书 / 抖音', value: '3', tone: 'green' },
  { title: '最近生成', desc: '最近 10 条记录', value: String(recent.value.length), tone: 'cyan' }
])
</script>

<template>
  <NGrid x-gap="14" y-gap="14" :cols="3">
    <NGridItem v-for="c in cards" :key="c.title">
      <NCard class="tile" size="small">
        <div class="row">
          <div>
            <div class="t">{{ c.title }}</div>
            <div class="d">{{ c.desc }}</div>
          </div>
          <div class="v">{{ c.value }}</div>
        </div>
      </NCard>
    </NGridItem>
  </NGrid>

  <NCard class="panel" size="small" style="margin-top: 14px">
    <template #header>最近生成</template>
    <div v-if="recent.length === 0">
      <NText depth="3">暂无记录。去「Agent 运行」生成一条。</NText>
    </div>
    <div v-else class="list">
      <div v-for="r in recent" :key="r.id" class="item">
        <div class="left">
          <NTag size="small" type="success" v-if="r.agent">{{ r.agent }}</NTag>
          <div class="meta">
            <span class="muted">#{{ r.id }}</span>
            <span class="dot">·</span>
            <span class="muted">{{ r.created_at }}</span>
          </div>
        </div>
        <div class="right muted">{{ r.model ?? '-' }}</div>
      </div>
    </div>
  </NCard>
</template>

<style scoped>
.tile {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
.row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}
.t {
  font-weight: 720;
}
.d {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}
.v {
  font-weight: 860;
  font-size: 26px;
  letter-spacing: -0.5px;
  opacity: 0.95;
}
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.meta {
  display: flex;
  gap: 8px;
  align-items: center;
}
.muted {
  color: var(--muted);
  font-size: 12px;
}
.dot {
  color: rgba(255, 255, 255, 0.22);
}
</style>

