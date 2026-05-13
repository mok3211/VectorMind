import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '@/views/LoginView.vue'
import ShellView from '@/views/ShellView.vue'
import DashboardView from '@/views/DashboardView.vue'
import AgentsView from '@/views/AgentsView.vue'
import RunsView from '@/views/RunsView.vue'
import MediaAccountsView from '@/views/MediaAccountsView.vue'
import WorkflowsView from '@/views/WorkflowsView.vue'
import PromptsView from '@/views/PromptsView.vue'
import MarketingView from '@/views/marketing/MarketingView.vue'
import RbacView from '@/views/RbacView.vue'

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
        { path: 'marketing', component: MarketingView },
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
