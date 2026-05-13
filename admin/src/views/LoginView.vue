<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { NButton, NCard, NForm, NFormItem, NInput, NText } from 'naive-ui'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref<string | null>(null)

async function onLogin() {
  error.value = null
  try {
    await auth.login(email.value, password.value)
    router.replace('/')
  } catch (e: any) {
    error.value = e?.response?.data?.detail ?? '登录失败'
  }
}
</script>

<template>
  <div class="wrap">
    <div class="brand">
      <div class="mark" />
      <div class="title">AI 工作流后台</div>
      <div class="sub">管理 Agent、提示词、内容生成与媒体账号</div>
    </div>

    <NCard class="card" size="large">
      <template #header>登录</template>
      <NForm @submit.prevent="onLogin">
        <NFormItem label="账号">
          <NInput v-model:value="email" placeholder="zhangchi" />
        </NFormItem>
        <NFormItem label="密码">
          <NInput v-model:value="password" type="password" placeholder="********" />
        </NFormItem>
        <div style="display:flex; gap:12px; align-items:center; justify-content:space-between">
          <NText depth="3" v-if="error">{{ error }}</NText>
          <div style="flex: 1" />
          <NButton type="primary" :loading="auth.loading" @click="onLogin">进入</NButton>
        </div>
      </NForm>
      <template #footer>
        <NText depth="3" style="font-size: 12px">
          默认内置管理员：zhangchi / zhangchi2026（仅当数据库没有任何用户时自动创建）
        </NText>
      </template>
    </NCard>
  </div>
</template>

<style scoped>
.wrap {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px;
}
.brand {
  position: fixed;
  top: 22px;
  left: 22px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  user-select: none;
}
.mark {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.6), transparent 55%),
    linear-gradient(135deg, rgba(124, 58, 237, 0.9), rgba(34, 197, 94, 0.7));
  box-shadow: 0 10px 30px rgba(124, 58, 237, 0.22);
}
.title {
  font-weight: 650;
  letter-spacing: 0.2px;
}
.sub {
  color: var(--muted);
  font-size: 12px;
}
.card {
  width: min(420px, 92vw);
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
</style>
