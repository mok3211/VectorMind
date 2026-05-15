<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NLayout, NLayoutContent, NLayoutHeader, NLayoutSider, NMenu, NText } from 'naive-ui'

const route = useRoute()
const router = useRouter()

const collapsed = ref(false)

const activeKey = computed(() => {
  const p = route.path || ''
  const parts = p.split('/').filter(Boolean)
  if (parts[0] !== 'marketing') return 'overview'
  return parts.slice(1).join('/') || 'overview'
})

const title = computed(() => String(route.meta?.title || '运营中心'))

const menuOptions = [
  {
    type: 'group',
    key: 'g-account',
    label: '账号体系',
    children: [
      { key: 'overview', label: '总览' },
      { key: 'accounts', label: '媒体账号' },
      { key: 'sessions', label: '会话（Session）' },
      { key: 'creators', label: '达人库' }
    ]
  },
  {
    type: 'group',
    key: 'g-ops',
    label: '运营工作台',
    children: [
      { key: 'ingest', label: '收录/导入' },
      { key: 'search/videos', label: '视频搜索' },
      { key: 'search/creators', label: '达人搜索' },
      { key: 'track/media', label: '内容监控池' },
      { key: 'track/comments', label: '评论监控池' },
      { key: 'contents', label: '内容/指标' },
      { key: 'interactions', label: '互动记录' }
    ]
  },
  {
    type: 'group',
    key: 'g-auto',
    label: '自动化',
    children: [{ key: 'jobs', label: '任务' }]
  }
] as any[]

function go(key: string) {
  router.push(`/marketing/${key}`)
}

watchEffect(() => {
  if (route.path === '/marketing') router.replace('/marketing/overview')
})
</script>

<template>
  <NLayout has-sider class="mkt">
    <NLayoutSider
      class="sider"
      bordered
      :width="260"
      :collapsed-width="76"
      collapse-mode="width"
      show-trigger
      :collapsed="collapsed"
      @collapse="collapsed = true"
      @expand="collapsed = false"
    >
      <div class="brand" :data-collapsed="collapsed ? '1' : '0'">
        <div class="logo">◈</div>
        <div class="wordmark">
          <div class="name">运营中心</div>
          <div class="desc">搜索 · 监控 · 互动 · 自动化</div>
        </div>
      </div>

      <NMenu :value="activeKey" :options="menuOptions" :collapsed="collapsed" @update:value="go" />

      <div class="sider-footer" :data-collapsed="collapsed ? '1' : '0'">
        <NText depth="3" class="hint">先把账号与会话稳定，再叠加任务与监控</NText>
      </div>
    </NLayoutSider>

    <NLayout>
      <NLayoutHeader class="header" bordered>
        <div class="header-left">
          <div class="title">{{ title }}</div>
          <div class="sub">按模块分层，避免所有能力堆在同一页</div>
        </div>
        <div class="header-right">
          <NButton secondary size="small" @click="router.push('/marketing/sessions')">去扫码登录</NButton>
          <NButton tertiary size="small" @click="router.push('/marketing/track/media')">去监控池</NButton>
        </div>
      </NLayoutHeader>

      <NLayoutContent class="content">
        <RouterView />
      </NLayoutContent>
    </NLayout>
  </NLayout>
</template>

<style scoped>
.mkt {
  min-height: calc(100vh - 24px);
}

.sider {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.02));
  backdrop-filter: blur(14px);
}

.brand {
  display: grid;
  grid-template-columns: 36px 1fr;
  align-items: center;
  gap: 10px;
  padding: 14px 14px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.brand[data-collapsed='1'] {
  grid-template-columns: 36px;
  justify-items: center;
}

.logo {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.06));
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 18px;
}

.wordmark {
  display: grid;
  gap: 2px;
}

.brand[data-collapsed='1'] .wordmark {
  display: none;
}

.name {
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.1;
}

.desc {
  font-size: 12px;
  opacity: 0.72;
}

.sider-footer {
  padding: 12px 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.sider-footer[data-collapsed='1'] {
  display: none;
}

.hint {
  font-size: 12px;
  opacity: 0.7;
}

.header {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.02));
  backdrop-filter: blur(14px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 16px;
}

.header-left {
  display: grid;
  gap: 2px;
}

.title {
  font-weight: 800;
  letter-spacing: 0.01em;
  line-height: 1.1;
}

.sub {
  font-size: 12px;
  opacity: 0.72;
}

.header-right {
  display: flex;
  gap: 10px;
}

.content {
  padding: 14px;
}
</style>
