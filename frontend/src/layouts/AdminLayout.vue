<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  Settings,
  Cpu,
  ClipboardList,
  LogOut,
  Menu,
  X,
} from '@lucide/vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const sidebarOpen = ref(false)

const navItems = [
  { path: '/admin/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/admin/knowledge-bases', label: '知识库', icon: BookOpen },
  { path: '/admin/documents', label: '文档', icon: FileText },
  { path: '/admin/rag-config', label: 'RAG 配置', icon: Settings },
  { path: '/admin/models', label: '模型', icon: Cpu },
  { path: '/admin/qa-logs', label: 'QA 日志', icon: ClipboardList },
]

async function handleLogout() {
  await authStore.logout()
  router.push('/admin/login')
}
</script>

<template>
  <div class="flex h-screen bg-muted/30">
    <!-- Sidebar -->
    <aside
      class="fixed inset-y-0 left-0 z-40 w-60 bg-background border-r border-border flex flex-col transition-transform duration-200 lg:static lg:translate-x-0"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <div class="flex h-16 items-center justify-between px-6 border-b border-border">
        <router-link to="/admin/dashboard" class="text-lg font-bold text-primary">
          管理后台
        </router-link>
        <button class="lg:hidden" @click="sidebarOpen = false">
          <X class="h-5 w-5" />
        </button>
      </div>
      <nav class="flex-1 px-3 py-4 space-y-1">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          :class="
            route.path === item.path
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'
          "
        >
          <component :is="item.icon" class="h-5 w-5" />
          {{ item.label }}
        </router-link>
      </nav>
      <div class="border-t border-border p-4">
        <button
          @click="handleLogout"
          class="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <LogOut class="h-5 w-5" />
          退出登录
        </button>
      </div>
    </aside>

    <!-- Overlay -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-30 bg-black/50 lg:hidden"
      @click="sidebarOpen = false"
    />

    <!-- Main -->
    <div class="flex-1 flex flex-col overflow-hidden">
      <header class="flex h-16 items-center gap-4 border-b border-border bg-background px-6">
        <button class="lg:hidden" @click="sidebarOpen = true">
          <Menu class="h-6 w-6" />
        </button>
        <div class="flex-1" />
        <span class="text-sm text-muted-foreground">{{ authStore.admin?.username }}</span>
      </header>
      <main class="flex-1 overflow-auto p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>
