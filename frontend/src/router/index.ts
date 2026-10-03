import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { resolveGuard } from '@/utils/guard'

/** 管理页挂 DashboardShell(二级标签导航),URL 根级大驼峰;壳层由 App.vue 统一包裹 */
function adminRoute(path: string, name: string, component: () => Promise<unknown>) {
  return {
    path,
    component: () => import('@/components/shell/DashboardShell.vue'),
    children: [{ path: '', name, component }],
    meta: { admin: true },
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Home', component: () => import('@/views/Home.vue'), meta: { public: true } },
    { path: '/docs', name: 'Docs', component: () => import('@/views/Docs.vue'), meta: { public: true } },
    { path: '/chat', name: 'Chat', component: () => import('@/views/Chat.vue'), meta: { public: true } },
    { path: '/Login', name: 'Login', component: () => import('@/views/admin/Login.vue'), meta: { public: true } },
    { path: '/Initialize', name: 'Initialize', component: () => import('@/views/admin/Initialize.vue'), meta: { public: true } },
    adminRoute('/Dashboard', 'Dashboard', () => import('@/views/admin/Dashboard.vue')),
    adminRoute('/KnowledgeBases', 'KnowledgeBases', () => import('@/views/admin/KnowledgeBases.vue')),
    adminRoute('/Documents', 'Documents', () => import('@/views/admin/Documents.vue')),
    adminRoute('/QaLogs', 'QaLogs', () => import('@/views/admin/QaLogs.vue')),
    adminRoute('/Settings', 'Settings', () => import('@/views/admin/Settings.vue')),
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

// 守卫判定抽到 utils/guard(纯函数,可 vitest 覆盖);登录态从 auth store 读取
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  const target = resolveGuard(
    { name: to.name as string | undefined, fullPath: to.fullPath, query: to.query, meta: to.meta },
    { token: auth.token, mustChangePassword: auth.mustChangePassword },
  )
  return target
})

export default router
