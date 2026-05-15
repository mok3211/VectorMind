<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NGrid, NGridItem, NStatistic, NTag, NText } from 'naive-ui'
import { api } from '@/lib/api'

const router = useRouter()
const loading = ref(false)

const counts = ref({ accounts: 0, connected: 0, expired: 0, disconnected: 0 })

const health = computed(() => {
  if (counts.value.accounts === 0) return { type: 'warning' as const, text: '还没有媒体账号' }
  if (counts.value.connected === 0) return { type: 'warning' as const, text: '账号未登录（请先扫码）' }
  return { type: 'success' as const, text: '账号已就绪' }
})

async function loadCounts() {
  loading.value = true
  try {
    const { data } = await api.get('/api/media-accounts')
    const items: any[] = Array.isArray(data?.items) ? data.items : []
    const connected = items.filter((x) => x?.status === 'connected').length
    const expired = items.filter((x) => x?.status === 'expired').length
    const disconnected = items.filter((x) => x?.status === 'disconnected').length
    counts.value = { accounts: items.length, connected, expired, disconnected }
  } catch {
    counts.value = { accounts: 0, connected: 0, expired: 0, disconnected: 0 }
  } finally {
    loading.value = false
  }
}

onMounted(loadCounts)
</script>

<template>
  <div class="wrap">
    <div class="hero">
      <div class="hero-left">
        <div class="kicker">运营中心 · 分层工作流</div>
        <div class="headline">先把账号跑通，再让运营自动化</div>
        <div class="lead">
          <NTag :type="health.type" size="small">{{ health.text }}</NTag>
          <NText depth="3" class="lead-text">
            推荐路径：媒体账号 → 扫码登录 → 搜索目标 → 放入监控池 → 任务调度 → 互动/发布
          </NText>
        </div>
      </div>
      <div class="hero-right">
        <NButton type="primary" @click="router.push('/marketing/accounts')">创建账号</NButton>
        <NButton secondary @click="router.push('/marketing/sessions')">扫码登录</NButton>
        <NButton tertiary @click="router.push('/marketing/track/media')">去监控池</NButton>
      </div>
    </div>

    <NGrid :cols="1" x-gap="12" y-gap="12">
      <NGridItem>
        <NCard size="small" class="tile" :segmented="{ content: true }" :bordered="false">
          <template #header>账号体系</template>
          <div class="stats">
            <NStatistic label="媒体账号" :value="counts.accounts" />
            <NStatistic label="已登录" :value="counts.connected" />
          </div>
          <div class="actions">
            <NButton size="small" secondary :loading="loading" @click="loadCounts">刷新</NButton>
            <NButton size="small" type="primary" @click="router.push('/marketing/sessions')">去登录</NButton>
          </div>
        </NCard>
      </NGridItem>
    </NGrid>
  </div>
</template>

<style scoped>
.wrap {
  display: grid;
  gap: 12px;
}

.hero {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: radial-gradient(1200px 500px at 20% 0%, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.03));
  backdrop-filter: blur(12px);
  padding: 16px;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
}

.hero-left {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.kicker {
  font-size: 12px;
  opacity: 0.7;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.headline {
  font-weight: 900;
  letter-spacing: 0.01em;
  font-size: 18px;
  line-height: 1.2;
}

.lead {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.lead-text {
  font-size: 12px;
  opacity: 0.75;
}

.hero-right {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tile {
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
}

.stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
}
</style>
