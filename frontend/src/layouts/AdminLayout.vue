<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  LayoutDashboard, Database, FileText, Settings, Cpu, ScrollText, LogOut,
} from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const nav = [
  { to: '/admin/dashboard', label: '仪表盘', icon: LayoutDashboard },
  { to: '/admin/knowledge-bases', label: '知识库', icon: Database },
  { to: '/admin/documents', label: '文档', icon: FileText },
  { to: '/admin/rag-config', label: 'RAG 配置', icon: Settings },
  { to: '/admin/models', label: '模型', icon: Cpu },
  { to: '/admin/qa-logs', label: '问答日志', icon: ScrollText },
]

async function onLogout() {
  await auth.logout()
  router.push('/admin/login')
}
</script>

<template>
  <div class="flex min-h-screen bg-muted/40">
    <aside class="flex w-56 flex-col border-r bg-background">
      <div class="px-4 py-5 text-lg font-semibold">管理后台</div>
      <nav class="flex-1 space-y-1 px-2">
        <router-link
          v-for="item in nav" :key="item.to" :to="item.to"
          class="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"
          :class="{ 'bg-accent font-medium': route.path === item.to }"
        >
          <component :is="item.icon" class="h-4 w-4" />
          {{ item.label }}
        </router-link>
      </nav>
      <button class="m-2 flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent" @click="onLogout">
        <LogOut class="h-4 w-4" /> 退出登录
      </button>
    </aside>
    <main class="flex-1 p-6">
      <router-view />
    </main>
  </div>
</template>
