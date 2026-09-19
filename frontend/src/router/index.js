import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'Chat',
    component: () => import('@/views/Chat.vue'),
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
    children: [
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

export default router
