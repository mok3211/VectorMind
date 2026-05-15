<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCard, NForm, NFormItem, NInput, NSelect, NSwitch, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

const router = useRouter()
const message = useMessage()

const tmPlatform = ref<'xhs' | 'douyin'>('xhs')
const tmMediaId = ref('')
const tmUrl = ref('')
const tmTitle = ref('')
const tmSource = ref('')
const tmCreateUser = ref('')
const tmIsComment = ref(false)

const tcPlatform = ref<'xhs' | 'douyin'>('xhs')
const tcMediaId = ref('')
const tcUrl = ref('')
const tcTitle = ref('')
const tcUserNickname = ref('')
const tcCreateUser = ref('')

const loading = ref(false)

async function createTrackMedia() {
  if (!tmMediaId.value.trim()) {
    message.error('platform_content_id 不能为空')
    return
  }
  loading.value = true
  try {
    await api.post('/api/marketing/track-media', {
      platform: tmPlatform.value,
      platform_content_id: tmMediaId.value.trim(),
      url: tmUrl.value.trim() || null,
      title: tmTitle.value.trim() || null,
      source: tmSource.value.trim() || null,
      create_user: tmCreateUser.value.trim() || null,
      is_comment: tmIsComment.value
    })
    message.success('已加入内容监控池')
    tmMediaId.value = ''
    tmUrl.value = ''
    tmTitle.value = ''
    tmSource.value = ''
    tmCreateUser.value = ''
    tmIsComment.value = false
  } finally {
    loading.value = false
  }
}

async function createTrackComment() {
  if (!tcMediaId.value.trim()) {
    message.error('platform_content_id 不能为空')
    return
  }
  loading.value = true
  try {
    await api.post('/api/marketing/track-comments', {
      platform: tcPlatform.value,
      platform_content_id: tcMediaId.value.trim(),
      url: tcUrl.value.trim() || null,
      title: tcTitle.value.trim() || null,
      user_nickname: tcUserNickname.value.trim() || null,
      create_user: tcCreateUser.value.trim() || null
    })
    message.success('已加入评论监控池')
    tcMediaId.value = ''
    tcUrl.value = ''
    tcTitle.value = ''
    tcUserNickname.value = ''
    tcCreateUser.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(() => {})
</script>

<template>
  <div class="wrap">
    <NCard size="small" class="sub">
      <template #header>收录内容（进入内容监控池）</template>
      <NForm>
        <div class="row">
          <NFormItem label="平台" style="width: 160px">
            <NSelect v-model:value="tmPlatform" :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]" />
          </NFormItem>
          <NFormItem label="media_id" style="flex: 1">
            <NInput v-model:value="tmMediaId" placeholder="平台内容ID（noctua 的 media_id）" />
          </NFormItem>
        </div>
        <NFormItem label="URL">
          <NInput v-model:value="tmUrl" placeholder="可选（后续用于跳转/定位）" />
        </NFormItem>
        <NFormItem label="标题">
          <NInput v-model:value="tmTitle" placeholder="可选（便于检索）" />
        </NFormItem>
        <div class="row">
          <NFormItem label="来源" style="flex: 1">
            <NInput v-model:value="tmSource" placeholder="关键词/导入批次/榜单" />
          </NFormItem>
          <NFormItem label="创建者" style="width: 240px">
            <NInput v-model:value="tmCreateUser" placeholder="可选" />
          </NFormItem>
          <NFormItem label="评论维护" style="width: 160px">
            <NSwitch v-model:value="tmIsComment" />
          </NFormItem>
        </div>
        <div class="actions">
          <NButton tertiary @click="router.push('/marketing/track/media')">查看内容监控池</NButton>
          <NButton type="primary" :loading="loading" @click="createTrackMedia">收录</NButton>
        </div>
      </NForm>
    </NCard>

    <NCard size="small" class="sub">
      <template #header>收录评论监控（进入评论监控池）</template>
      <NForm>
        <div class="row">
          <NFormItem label="平台" style="width: 160px">
            <NSelect v-model:value="tcPlatform" :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]" />
          </NFormItem>
          <NFormItem label="media_id" style="flex: 1">
            <NInput v-model:value="tcMediaId" placeholder="平台内容ID" />
          </NFormItem>
        </div>
        <NFormItem label="URL">
          <NInput v-model:value="tcUrl" placeholder="可选" />
        </NFormItem>
        <NFormItem label="标题">
          <NInput v-model:value="tcTitle" placeholder="可选" />
        </NFormItem>
        <div class="row">
          <NFormItem label="用户昵称" style="flex: 1">
            <NInput v-model:value="tcUserNickname" placeholder="可选（用于筛选/追踪）" />
          </NFormItem>
          <NFormItem label="创建者" style="width: 240px">
            <NInput v-model:value="tcCreateUser" placeholder="可选" />
          </NFormItem>
        </div>
        <div class="actions">
          <NButton tertiary @click="router.push('/marketing/track/comments')">查看评论监控池</NButton>
          <NButton type="primary" :loading="loading" @click="createTrackComment">收录</NButton>
        </div>
      </NForm>
    </NCard>
  </div>
</template>

<style scoped>
.wrap {
  display: grid;
  gap: 12px;
}
.sub {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.05);
  border-radius: 14px;
}
.row {
  display: flex;
  gap: 12px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

