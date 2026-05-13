<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { NButton, NCard, NDataTable, NForm, NFormItem, NInput, NSelect, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()
const items = ref<any[]>([])
const loading = ref(false)

const platform = ref<'xhs' | 'douyin'>('xhs')
const profileType = ref<'owned' | 'competitor'>('owned')
const secUid = ref<string | null>(null)
const nickname = ref<string | null>(null)
const userLink = ref<string | null>(null)

async function reload() {
  loading.value = true
  try {
    const { data } = await api.get('/api/marketing/profiles?limit=200')
    items.value = data.items
  } finally {
    loading.value = false
  }
}

async function createOne() {
  await api.post('/api/marketing/profiles', {
    platform: platform.value,
    profile_type: profileType.value,
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
  { title: '类型', key: 'profile_type', width: 120 },
  { title: 'sec_uid', key: 'sec_uid', width: 220 },
  { title: '昵称', key: 'nickname' },
  { title: '状态', key: 'status', width: 120 },
  { title: '风控', key: 'risk_status', width: 120 }
]
</script>

<template>
  <NCard size="small" class="sub">
    <template #header>新增账号/竞品</template>
    <NForm>
      <div class="row">
        <NFormItem label="平台" style="flex: 1">
          <NSelect v-model:value="platform" :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]" />
        </NFormItem>
        <NFormItem label="类型" style="flex: 1">
          <NSelect
            v-model:value="profileType"
            :options="[{ label: '自有账号', value: 'owned' }, { label: '竞品/监控', value: 'competitor' }]"
          />
        </NFormItem>
      </div>
      <NFormItem label="sec_uid">
        <NInput v-model:value="secUid" placeholder="可先为空，后续采集后补齐" />
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
    <template #header>账号列表</template>
    <NDataTable :columns="columns" :data="items" :loading="loading" />
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

