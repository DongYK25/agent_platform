import { createRouter, createWebHistory } from 'vue-router'
import AppShell from '../layouts/AppShell.vue'
import { session } from '../session'
import ChatView from '../views/ChatView.vue'
import LoginView from '../views/LoginView.vue'
import UsersView from '../views/UsersView.vue'
import WorkOrdersView from '../views/WorkOrdersView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    title?: string
    fill?: boolean
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      component: LoginView,
      meta: { public: true, title: '登录' },
    },
    {
      path: '/',
      component: AppShell,
      children: [
        { path: '', redirect: '/work-orders' },
        { path: 'users', component: UsersView, meta: { title: '用户' } },
        { path: 'work-orders', component: WorkOrdersView, meta: { title: '工单' } },
        { path: 'chat', component: ChatView, meta: { title: '对话', fill: true } },
      ],
    },
  ],
})

router.beforeEach((to) => {
  if (to.path === '/login' && session.token) return '/work-orders'
  if (to.meta.public || session.token) return true
  return { path: '/login', query: { redirect: to.fullPath } }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 工单台` : '工单台'
})
