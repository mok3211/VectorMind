<script setup lang="ts">
import { h, onMounted, ref } from 'vue'
import { NButton, NCard, NDataTable, NForm, NFormItem, NInput, NSelect, NSwitch, NTabs, NTabPane, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()
const loading = ref(false)

// track media
const trackMedia = ref<any[]>([])
const tmPlatform = ref<'xhs' | 'douyin'>('xhs')
const tmMediaId = ref('')
const tmUrl = ref('')
const tmTitle = ref('')
const tmSource = ref('')
const tmCreateUser = ref('')
const tmIsComment = ref(false)

// track comments
const trackComments = ref<any[]>([])
const tcPlatform = ref<'xhs' | 'douyin'>('xhs')
const tcMediaId = ref('')
const tcUrl = ref('')
const tcTitle = ref('')
const tcUserNickname = ref('')
const tcCreateUser = ref('')

async function reload() {
  loading.value = true
  try {
    const [a, b] = await Promise.all([api.get('/api/marketing/track-media?limit=200'), api.get('/api/marketing/track-comments?limit=200')])
    trackMedia.value = a.data.items
    trackComments.value = b.data.items
  } finally {
    loading.value = false
  }
}

async function createTrackMedia() {
  if (!tmMediaId.value.trim()) {
    message.error('platform_content_id 不能为空')
    return
  }
  await api.post('/api/marketing/track-media', {
    platform: tmPlatform.value,
    platform_content_id: tmMediaId.value.trim(),
    url: tmUrl.value.trim() || null,
    title: tmTitle.value.trim() || null,
    source: tmSource.value.trim() || null,
    create_user: tmCreateUser.value.trim() || null,
    is_comment: tmIsComment.value
  })
  message.success('已加入内容监控')
  tmMediaId.value = ''
  tmUrl.value = ''
  tmTitle.value = ''
  tmSource.value = ''
  tmCreateUser.value = ''
  tmIsComment.value = false
  await reload()
}

async function toggleComment(row: any) {
  await api.put(`/api/marketing/track-media/${row.id}/toggle-comment?enable=${!row.is_comment}`)
  await reload()
}

async function sendComment(row: any) {
  const text = window.prompt('请输入要发送的评论内容：', '路过支持一下～')
  if (!text) return
  // 调试建议：先 headful + slowmo
  const { data } = await api.post('/api/marketing/send-comment', {
    platform: row.platform,
    track_media_id: row.id,
    text,
    headless: false,
    slow_mo_ms: 200
  })
  if (data.ok) message.success('已提交评论（请到互动记录查看结果）')
  else message.error(`评论失败：${data.detail}`)
  await reload()
}

async function createTrackComment() {
  if (!tcMediaId.value.trim()) {
    message.error('platform_content_id 不能为空')
    return
  }
  await api.post('/api/marketing/track-comments', {
    platform: tcPlatform.value,
    platform_content_id: tcMediaId.value.trim(),
    url: tcUrl.value.trim() || null,
    title: tcTitle.value.trim() || null,
    user_nickname: tcUserNickname.value.trim() || null,
    create_user: tcCreateUser.value.trim() || null
  })
  message.success('已加入评论监控')
  tcMediaId.value = ''
  tcUrl.value = ''
  tcTitle.value = ''
  tcUserNickname.value = ''
  tcCreateUser.value = ''
  await reload()
}

async function deleteTrackComment(row: any) {
  await api.delete(`/api/marketing/track-comments/${row.id}`)
  message.success('已删除（软删）')
  await reload()
}

onMounted(reload)

const tmColumns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '平台', key: 'platform', width: 90 },
  { title: 'media_id', key: 'platform_content_id', width: 200 },
  { title: '标题', key: 'title' },
  { title: '来源', key: 'source', width: 160 },
  { title: '评论维护', key: 'is_comment', width: 110 },
  { title: '状态', key: 'status', width: 90 },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    render(row: any) {
      return h('div', { style: 'display:flex; gap:8px' }, [
        h(
          NButton,
          { size: 'small', secondary: true, onClick: () => toggleComment(row) },
          { default: () => (row.is_comment ? '关闭评论维护' : '开启评论维护') }
        ),
        h(
          NButton,
          { size: 'small', type: 'primary', secondary: true, onClick: () => sendComment(row) },
          { default: () => '评论' }
        )
      ])
    }
  }
]

const tcColumns = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '平台', key: 'platform', width: 90 },
  { title: 'media_id', key: 'platform_content_id', width: 200 },
  { title: '标题', key: 'title' },
  { title: '用户昵称', key: 'user_nickname', width: 160 },
  { title: '状态', key: 'track_status', width: 90 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render(row: any) {
      return h(
        NButton,
        { size: 'small', secondary: true, onClick: () => deleteTrackComment(row) },
        { default: () => '删除' }
      )
    }
  }
]
</script>

<template>
  <NTabs type="segment">
    <NTabPane name="media" tab="内容监控">
      <NCard size="small" class="sub">
        <template #header>新增内容监控项</template>
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
            <NInput v-model:value="tmUrl" placeholder="可选" />
          </NFormItem>
          <NFormItem label="标题">
            <NInput v-model:value="tmTitle" placeholder="可选" />
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
          <div style="display:flex; justify-content:flex-end; gap: 10px">
            <NButton secondary @click="reload">刷新</NButton>
            <NButton type="primary" @click="createTrackMedia">加入监控</NButton>
          </div>
        </NForm>
      </NCard>

      <NCard size="small" class="sub" style="margin-top: 12px">
        <template #header>内容监控列表</template>
        <NDataTable :columns="tmColumns" :data="trackMedia" :loading="loading" />
      </NCard>
    </NTabPane>

    <NTabPane name="comments" tab="评论监控">
      <NCard size="small" class="sub">
        <template #header>新增评论监控项</template>
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
          <div style="display:flex; justify-content:flex-end; gap: 10px">
            <NButton secondary @click="reload">刷新</NButton>
            <NButton type="primary" @click="createTrackComment">加入监控</NButton>
          </div>
        </NForm>
      </NCard>

      <NCard size="small" class="sub" style="margin-top: 12px">
        <template #header>评论监控列表</template>
        <NDataTable :columns="tcColumns" :data="trackComments" :loading="loading" />
      </NCard>
    </NTabPane>
  </NTabs>
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
