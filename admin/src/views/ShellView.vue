<script setup lang="ts">
import { onMounted } from 'vue'
import { NConfigProvider, NDialogProvider, NMessageProvider, darkTheme } from 'naive-ui'
import SideNav from '@/components/SideNav.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

onMounted(async () => {
  if (!auth.me) {
    try {
      await auth.fetchMe()
    } catch {
      // ignore: router guard will redirect
    }
  }
})

const themeOverrides = {
  common: {
    primaryColor: '#7c3aed',
    primaryColorHover: '#8b5cf6',
    primaryColorPressed: '#6d28d9'
  }
}
</script>

<template>
  <NConfigProvider :theme="darkTheme" :theme-overrides="themeOverrides">
    <NMessageProvider>
      <NDialogProvider>
        <div class="grid">
          <SideNav class="side" />
          <main class="main">
            <div class="top">
              <div class="kicker">AI 工作流</div>
              <div class="headline">运营控制台</div>
              <div class="hint">生成内容 → 记录追踪 → 导出平台文案 →（后续接）自动发布</div>
            </div>
            <router-view />
          </main>
        </div>
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
}
.main {
  padding: 22px 22px 28px;
}
.top {
  padding: 12px 14px 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
  margin-bottom: 16px;
}
.kicker {
  color: var(--muted);
  font-size: 12px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}
.headline {
  font-weight: 820;
  font-size: 22px;
  letter-spacing: -0.2px;
  margin-top: 4px;
}
.hint {
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
}
@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .side {
    position: relative;
    height: auto;
  }
}
</style>

