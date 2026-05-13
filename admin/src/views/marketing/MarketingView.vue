<script setup lang="ts">
import { NCard, NTabs, NTabPane } from 'naive-ui'
import ProfilesPane from './ProfilesPane.vue'
import SessionsPane from './SessionsPane.vue'
import JobsPane from './JobsPane.vue'
import TrackPane from './TrackPane.vue'
import InteractionsPane from './InteractionsPane.vue'
import ContentsPane from './ContentsPane.vue'
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>Marketing</template>
    <NTabs type="segment">
      <NTabPane name="profiles" tab="账号">
        <ProfilesPane />
      </NTabPane>
      <NTabPane name="sessions" tab="会话">
        <SessionsPane />
      </NTabPane>
      <NTabPane name="jobs" tab="任务">
        <JobsPane />
      </NTabPane>
      <NTabPane name="track" tab="监控">
        <TrackPane />
      </NTabPane>
      <NTabPane name="interactions" tab="互动记录">
        <InteractionsPane />
      </NTabPane>
      <NTabPane name="contents" tab="内容/指标">
        <ContentsPane />
      </NTabPane>
    </NTabs>
  </NCard>
</template>

<style scoped>
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
</style>
