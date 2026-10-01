import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

/** 管理页统一挂 AdminLayout 外壳,URL 为根级大驼峰(/Dashboard 等),不带 /admin/ 前缀 */
function adminRoute(path: string, name: string, component: () => Promise<unknown>) {
  return {
    path,
    component: () => import('@/layouts/AdminLayout.vue'),
    children: [{ path: '', name, component }],
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Chat', component: () => import('@/views/Chat.vue'), meta: { public: true } },
    { path: '/Login', name: 'Login', component: () => import('@/views/admin/Login.vue'), meta: { public: true } },
    { path: '/Initialize', name: 'Initialize', component: () => import('@/views/admin/Initialize.vue'), meta: { public: true } },
    adminRoute('/Dashboard', 'Dashboard', () => import('@/views/admin/Dashboard.vue')),
    adminRoute('/KnowledgeBases', 'KnowledgeBases', () => import('@/views/admin/KnowledgeBases.vue')),
    adminRoute('/Documents', 'Documents', () => import('@/views/admin/Documents.vue')),
    adminRoute('/RagConfig', 'RagConfig', () => import('@/views/admin/RagConfig.vue')),
    adminRoute('/Models', 'Models', () => import('@/views/admin/Models.vue')),
    adminRoute('/QaLogs', 'QaLogs', () => import('@/views/admin/QaLogs.vue')),
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

// 守卫按 meta.public 判定公开页;管理页要求登录,强制改密期间拦截到 /Initialize
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.public) {
    // 已登录(且无需改密)再访问登录页,直接送进仪表盘
    if (to.name === 'Login' && auth.token && !auth.mustChangePassword) return '/Dashboard'
    return true
  }
  if (!auth.token) return '/Login'
  if (auth.mustChangePassword) return '/Initialize'
  return true
})

export default router
