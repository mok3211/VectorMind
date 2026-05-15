<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NCard, NDataTable, NForm, NFormItem, NInput, NSelect, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()
const items = ref<any[]>([])
const loading = ref(false)

const platform = ref<'xhs' | 'douyin'>('xhs')
const secUid = ref<string | null>(null)
const nickname = ref<string | null>(null)
const userLink = ref<string | null>(null)

async function reload() {
  loading.value = true
  try {
    const { data } = await api.get('/api/marketing/profiles?profile_type=competitor&limit=200')
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function createOne() {
  await api.post('/api/marketing/profiles', {
    platform: platform.value,
    profile_type: 'competitor',
    sec_uid: secUid.value,
    nickname: nickname.value,
    user_link: userLink.value
  })
  message.success('已创建')
  secUid.value = null
  nickname.value = null
  userLink.value = null
  await reload()
}

onMounted(reload)

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '平台', key: 'platform', width: 100 },
  { title: 'sec_uid', key: 'sec_uid', width: 240 },
  { title: '昵称', key: 'nickname', minWidth: 220, ellipsis: { tooltip: true } },
  { title: '状态', key: 'status', width: 120 },
  { title: '风控', key: 'risk_status', width: 120 }
]
</script>

<template>
  <NCard size="small" class="sub">
    <template #header>新增达人</template>
    <NForm>
      <div class="row">
        <NFormItem label="平台" style="flex: 1">
          <NSelect v-model:value="platform" :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]" />
        </NFormItem>
      </div>
      <NFormItem label="sec_uid">
        <NInput v-model:value="secUid" placeholder="可选（有则更准）" />
      </NFormItem>
      <NFormItem label="昵称">
        <NInput v-model:value="nickname" placeholder="可选" />
      </NFormItem>
      <NFormItem label="主页链接">
        <NInput v-model:value="userLink" placeholder="https://..." />
      </NFormItem>
      <div style="display:flex; justify-content:flex-end; gap: 10px">
        <NButton secondary @click="reload">刷新</NButton>
        <NButton type="primary" @click="createOne">创建</NButton>
      </div>
    </NForm>
  </NCard>

  <NCard size="small" class="sub" style="margin-top: 12px">
    <template #header>达人列表</template>
    <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="980" />
  </NCard>
</template>

<style scoped>
.sub {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
}
.row {
  display: flex;
  gap: 12px;
}
</style>
