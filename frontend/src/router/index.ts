import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('@/views/Chat.vue') },
    { path: '/admin/login', component: () => import('@/views/admin/Login.vue'), meta: { public: true } },
    { path: '/admin/initialize', component: () => import('@/views/admin/Initialize.vue'), meta: { public: true } },
    {
      path: '/admin',
      component: () => import('@/layouts/AdminLayout.vue'),
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', component: () => import('@/views/admin/Dashboard.vue') },
        { path: 'knowledge-bases', component: () => import('@/views/admin/KnowledgeBases.vue') },
        { path: 'documents', component: () => import('@/views/admin/Documents.vue') },
        { path: 'rag-config', component: () => import('@/views/admin/RagConfig.vue') },
        { path: 'models', component: () => import('@/views/admin/Models.vue') },
        { path: 'qa-logs', component: () => import('@/views/admin/QaLogs.vue') },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  if (!to.path.startsWith('/admin')) return true
  const auth = useAuthStore()
  if (to.meta.public) {
    if (auth.token && !auth.mustChangePassword && to.path === '/admin/login') return '/admin/dashboard'
    return true
  }
  if (!auth.token) return '/admin/login'
  if (auth.mustChangePassword) return '/admin/initialize'
  return true
})

export default router
