<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NDivider, NText } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/lib/api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const items = ref<{ key: string; label: string; icon?: string }[]>([
  { key: '/', label: '概览', icon: '◎' }
])

onMounted(async () => {
  try {
    const { data } = await api.get('/api/rbac/my-menus')
    const list = (data.items ?? []).map((m: any) => ({
      key: m.path,
      label: m.label,
      icon: m.icon || '•'
    }))
    // 确保有首页
    if (!list.find((x: any) => x.key === '/')) list.unshift({ key: '/', label: '概览', icon: '◎' })
    items.value = list
  } catch {
    // fallback: 保留最小菜单
  }
})

const active = computed(() => items.value.find((i) => route.path === i.key)?.key ?? '/')

function go(path: string) {
  router.push(path)
}

function logout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <aside class="nav">
    <div class="brand">
      <div class="mark" />
      <div class="words">
        <div class="title">Workflows</div>
        <div class="sub">Admin Console</div>
      </div>
    </div>

    <NDivider style="margin: 14px 0" />

    <div class="items">
      <button
        v-for="it in items"
        :key="it.key"
        class="item"
        :class="{ active: active === it.key }"
        @click="go(it.key)"
      >
        <span class="glyph">{{ it.icon }}</span>
        <span class="label">{{ it.label }}</span>
      </button>
    </div>

    <div class="bottom">
      <div class="me">
        <NText depth="3" style="font-size: 12px">当前用户</NText>
        <div style="font-weight: 600">{{ auth.me?.email ?? '-' }}</div>
      </div>
      <NButton secondary block @click="logout">退出登录</NButton>
    </div>
  </aside>
</template>

<style scoped>
.nav {
  height: 100vh;
  position: sticky;
  top: 0;
  padding: 18px 14px;
  border-right: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.04));
  backdrop-filter: blur(10px);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 8px 6px;
}
.mark {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.6), transparent 55%),
    linear-gradient(135deg, rgba(124, 58, 237, 0.9), rgba(34, 197, 94, 0.7));
  box-shadow: 0 10px 26px rgba(124, 58, 237, 0.22);
}
.words .title {
  font-weight: 760;
  letter-spacing: 0.2px;
  line-height: 1.1;
}
.words .sub {
  color: var(--muted);
  font-size: 12px;
}
.items {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
}
.item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    transform 160ms ease;
}
.item:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}
.item.active {
  background: linear-gradient(180deg, rgba(124, 58, 237, 0.18), rgba(255, 255, 255, 0.05));
  border-color: rgba(124, 58, 237, 0.35);
}
.glyph {
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  font-size: 13px;
}
.label {
  font-weight: 600;
  letter-spacing: 0.1px;
}
.bottom {
  margin-top: auto;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.me {
  padding: 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
</style>
