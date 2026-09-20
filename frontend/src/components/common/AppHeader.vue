<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { MessageSquare, Settings, LogIn, LogOut } from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const isAdminRoute = computed(() => route.path.startsWith('/admin'))

async function handleLogout() {
  await authStore.logout()
  router.push('/')
}
</script>

<template>
  <header class="flex h-14 items-center justify-between border-b border-border bg-background px-6">
    <div class="flex items-center gap-6">
      <router-link to="/" class="text-lg font-bold text-primary">
        Smart Campus RAG
      </router-link>
      <nav class="flex gap-1">
        <router-link
          to="/"
          class="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
          :class="!isAdminRoute ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground'"
        >
          <MessageSquare class="h-4 w-4" />
          聊天
        </router-link>
        <router-link
          to="/admin"
          class="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors"
          :class="isAdminRoute ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground'"
        >
          <Settings class="h-4 w-4" />
          管理后台
        </router-link>
      </nav>
    </div>
    <div class="flex items-center gap-4">
      <template v-if="authStore.isAuthenticated">
        <span class="text-sm text-muted-foreground">{{ authStore.admin?.username }}</span>
        <button
          @click="handleLogout"
          class="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <LogOut class="h-4 w-4" />
          退出
        </button>
      </template>
      <router-link
        v-else
        to="/admin/login"
        class="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <LogIn class="h-4 w-4" />
        登录
      </router-link>
    </div>
  </header>
</template>
