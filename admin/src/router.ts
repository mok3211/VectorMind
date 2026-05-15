import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import ShellView from '@/views/ShellView.vue'
import DashboardView from '@/views/DashboardView.vue'
import AgentsView from '@/views/AgentsView.vue'
import RunsView from '@/views/RunsView.vue'
import MediaAccountsView from '@/views/MediaAccountsView.vue'
import WorkflowsView from '@/views/WorkflowsView.vue'
import PromptsView from '@/views/PromptsView.vue'
import MarketingLayoutView from '@/views/marketing/MarketingLayoutView.vue'
import MarketingOverviewView from '@/views/marketing/MarketingOverviewView.vue'
import CreatorsPane from '@/views/marketing/CreatorsPane.vue'
import SessionsPane from '@/views/marketing/SessionsPane.vue'
import JobsPane from '@/views/marketing/JobsPane.vue'
import InteractionsPane from '@/views/marketing/InteractionsPane.vue'
import ContentsPane from '@/views/marketing/ContentsPane.vue'
import MarketingIngestView from '@/views/marketing/MarketingIngestView.vue'
import MarketingTrackMediaView from '@/views/marketing/MarketingTrackMediaView.vue'
import MarketingTrackCommentsView from '@/views/marketing/MarketingTrackCommentsView.vue'
import MarketingVideoSearchView from '@/views/marketing/MarketingVideoSearchView.vue'
import MarketingCreatorSearchView from '@/views/marketing/MarketingCreatorSearchView.vue'
import RbacView from '@/views/RbacView.vue'
import LlmSettingsView from '@/views/LlmSettingsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    {
      path: '/',
      component: ShellView,
      children: [
        { path: '', component: DashboardView },
        { path: 'agents', component: AgentsView },
        { path: 'workflows', component: WorkflowsView },
        { path: 'prompts', component: PromptsView },
        { path: 'llm', component: LlmSettingsView },
        {
          path: 'marketing',
          component: MarketingLayoutView,
          children: [
            { path: '', redirect: '/marketing/overview' },
            { path: 'overview', component: MarketingOverviewView, meta: { title: '总览' } },
            { path: 'accounts', component: MediaAccountsView, meta: { title: '媒体账号' } },
            { path: 'creators', component: CreatorsPane, meta: { title: '达人库' } },
            { path: 'sessions', component: SessionsPane, meta: { title: '会话（Session）' } },
            { path: 'ingest', component: MarketingIngestView, meta: { title: '收录/导入' } },
            { path: 'search/videos', component: MarketingVideoSearchView, meta: { title: '视频搜索' } },
            { path: 'search/creators', component: MarketingCreatorSearchView, meta: { title: '达人搜索' } },
            { path: 'track', redirect: '/marketing/track/media' },
            { path: 'track/media', component: MarketingTrackMediaView, meta: { title: '内容监控池' } },
            { path: 'track/comments', component: MarketingTrackCommentsView, meta: { title: '评论监控池' } },
            { path: 'jobs', component: JobsPane, meta: { title: '任务' } },
            { path: 'interactions', component: InteractionsPane, meta: { title: '互动记录' } },
            { path: 'contents', component: ContentsPane, meta: { title: '内容/指标' } }
          ]
        },
        { path: 'runs', component: RunsView },
        { path: 'media', component: MediaAccountsView },
        { path: 'rbac', component: RbacView }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (!token && to.path !== '/login') return '/login'
  return true
})
