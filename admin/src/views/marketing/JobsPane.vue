<script setup lang="ts">
import { h, onMounted, reactive, ref } from 'vue'
import { NButton, NCard, NDataTable, NForm, NFormItem, NInput, NSelect, useMessage } from 'naive-ui'
import { api } from '@/lib/api'

const message = useMessage()
const items = ref<any[]>([])
const runs = ref<any[]>([])
const loading = ref(false)

const name = ref('xhs 内容采集')
const platform = ref<'xhs' | 'douyin'>('xhs')
const jobType = ref('content_search')
const paramsJson = ref('{"keyword":"", "limit": 20}')

const filterPlatform = ref<string | null>(null)
const filterJobType = ref<string | null>(null)
const filterEnabled = ref<string | null>(null)
const runStatus = ref<string | null>(null)

const paginationJobs = reactive({
  page: 1,
  pageSize: 20,
  pageSizes: [20, 50, 100],
  itemCount: 0,
  showSizePicker: true,
  onChange: (p: number) => {
    paginationJobs.page = p
    reload()
  },
  onUpdatePageSize: (s: number) => {
    paginationJobs.pageSize = s
    paginationJobs.page = 1
    reload()
  }
})

const paginationRuns = reactive({
  page: 1,
  pageSize: 20,
  pageSizes: [20, 50, 100],
  itemCount: 0,
  showSizePicker: true,
  onChange: (p: number) => {
    paginationRuns.page = p
    reload()
  },
  onUpdatePageSize: (s: number) => {
    paginationRuns.pageSize = s
    paginationRuns.page = 1
    reload()
  }
})

async function reload() {
  loading.value = true
  try {
    const jq = new URLSearchParams()
    jq.set('page', String(paginationJobs.page))
    jq.set('page_size', String(paginationJobs.pageSize))
    if (filterPlatform.value) jq.set('platform', filterPlatform.value)
    if (filterJobType.value) jq.set('job_type', filterJobType.value)
    if (filterEnabled.value !== null) jq.set('enabled', filterEnabled.value)

    const rq = new URLSearchParams()
    rq.set('page', String(paginationRuns.page))
    rq.set('page_size', String(paginationRuns.pageSize))
    if (runStatus.value) rq.set('status', runStatus.value)

    const [j, r] = await Promise.all([api.get(`/api/marketing/jobs?${jq.toString()}`), api.get(`/api/marketing/job-runs?${rq.toString()}`)])
    items.value = j.data.items
    runs.value = r.data.items
    paginationJobs.itemCount = j.data.total ?? j.data.items?.length ?? 0
    paginationRuns.itemCount = r.data.total ?? r.data.items?.length ?? 0
  } finally {
    loading.value = false
  }
}

async function createOne() {
  let p: any = null
  try {
    p = paramsJson.value ? JSON.parse(paramsJson.value) : null
  } catch {
    message.error('params 不是合法 JSON')
    return
  }
  await api.post('/api/marketing/jobs', {
    name: name.value,
    platform: platform.value,
    job_type: jobType.value,
    params: p,
    enabled: true
  })
  message.success('已创建')
  await reload()
}

async function runOne(id: number) {
  await api.post(`/api/marketing/jobs/${id}/run`)
  message.success('已触发运行（后台执行）')
  await reload()
}

onMounted(reload)

const columns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '名称', key: 'name', minWidth: 320, ellipsis: { tooltip: true } },
  { title: '平台', key: 'platform', width: 100 },
  { title: '类型', key: 'job_type', width: 160 },
  { title: '启用', key: 'enabled', width: 90 },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    fixed: 'right' as const,
    render(row: any) {
      return h(
        NButton,
        { size: 'small', type: 'primary', secondary: true, onClick: () => runOne(row.id) },
        { default: () => '运行' }
      )
    }
  }
]

const runColumns = [
  { title: 'RunID', key: 'id', width: 80 },
  { title: 'JobID', key: 'job_id', width: 80 },
  { title: '状态', key: 'status', width: 120 },
  { title: '开始', key: 'started_at', width: 220 },
  { title: '结束', key: 'finished_at', width: 220 }
]
</script>

<template>
  <NCard size="small" class="sub">
    <template #header>新建任务</template>
    <NForm>
      <div class="row">
        <NFormItem label="名称" style="flex: 1">
          <NInput v-model:value="name" />
        </NFormItem>
        <NFormItem label="平台" style="width: 180px">
          <NSelect v-model:value="platform" :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]" />
        </NFormItem>
        <NFormItem label="类型" style="width: 200px">
          <NSelect
            v-model:value="jobType"
            :options="[
              { label: '内容搜索/采集', value: 'content_search' },
              { label: '内容指标刷新', value: 'content_metrics' },
              { label: '账号指标刷新', value: 'profile_metrics' },
              { label: '评论同步', value: 'comment_sync' },
              { label: '关键词榜单快照', value: 'keyword_snapshot' }
            ]"
          />
        </NFormItem>
      </div>
      <NFormItem label="params(JSON)">
        <NInput v-model:value="paramsJson" type="textarea" :autosize="{ minRows: 4, maxRows: 10 }" />
      </NFormItem>
      <div style="display:flex; justify-content:flex-end; gap: 10px">
        <NButton secondary @click="reload">刷新</NButton>
        <NButton type="primary" @click="createOne">创建</NButton>
      </div>
    </NForm>
  </NCard>

  <NCard size="small" class="sub" style="margin-top: 12px">
    <template #header>任务列表</template>
    <div style="display:flex; gap:10px; align-items:center; margin-bottom: 10px">
      <NSelect
        v-model:value="filterPlatform"
        clearable
        placeholder="平台"
        style="width: 160px"
        :options="[{ label: '小红书', value: 'xhs' }, { label: '抖音', value: 'douyin' }]"
      />
      <NSelect
        v-model:value="filterJobType"
        clearable
        placeholder="类型"
        style="width: 200px"
        :options="[
          { label: '内容搜索/采集', value: 'content_search' },
          { label: '内容指标刷新', value: 'content_metrics' },
          { label: '账号指标刷新', value: 'profile_metrics' },
          { label: '评论同步', value: 'comment_sync' },
          { label: '关键词榜单快照', value: 'keyword_snapshot' }
        ]"
      />
      <NSelect
        v-model:value="filterEnabled"
        clearable
        placeholder="启用"
        style="width: 140px"
        :options="[
          { label: '启用', value: 'true' },
          { label: '禁用', value: 'false' }
        ]"
      />
      <div style="flex: 1" />
      <NButton secondary :loading="loading" @click="reload">查询</NButton>
    </div>

    <NDataTable :columns="columns" :data="items" :loading="loading" :scroll-x="980" remote :pagination="paginationJobs" />
  </NCard>

  <NCard size="small" class="sub" style="margin-top: 12px">
    <template #header>运行记录</template>
    <div style="display:flex; gap:10px; align-items:center; margin-bottom: 10px">
      <NSelect
        v-model:value="runStatus"
        clearable
        placeholder="状态"
        style="width: 160px"
        :options="[
          { label: 'running', value: 'running' },
          { label: 'success', value: 'success' },
          { label: 'failed', value: 'failed' }
        ]"
      />
      <div style="flex: 1" />
      <NButton secondary :loading="loading" @click="reload">查询</NButton>
    </div>

    <NDataTable :columns="runColumns" :data="runs" :loading="loading" :scroll-x="820" remote :pagination="paginationRuns" />
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
