import { createRouter, createWebHistory } from 'vue-router'

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp ? payload.exp * 1000 < Date.now() : false
  } catch {
    return true
  }
}

const routes = [
  {
    path: '/',
    component: () => import('@/layouts/UserLayout.vue'),
    children: [
      { path: '', name: 'Chat', component: () => import('@/views/Chat.vue') },
    ],
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: () => import('@/views/admin/Login.vue'),
  },
  {
    path: '/admin/initialize',
    name: 'AdminInitialize',
    component: () => import('@/views/admin/Initialize.vue'),
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/admin/Dashboard.vue') },
      { path: 'knowledge-bases', name: 'KnowledgeBases', component: () => import('@/views/admin/KnowledgeBases.vue') },
      { path: 'documents', name: 'Documents', component: () => import('@/views/admin/Documents.vue') },
      { path: 'rag-config', name: 'RagConfig', component: () => import('@/views/admin/RagConfig.vue') },
      { path: 'models', name: 'Models', component: () => import('@/views/admin/Models.vue') },
      { path: 'qa-logs', name: 'QaLogs', component: () => import('@/views/admin/QaLogs.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  if (to.matched.some((record) => record.meta.requiresAuth)) {
    const token = localStorage.getItem('admin_token')
    if (!token || isTokenExpired(token)) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
      next({ name: 'AdminLogin' })
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
