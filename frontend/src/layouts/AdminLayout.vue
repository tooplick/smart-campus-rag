<script setup lang="ts">
// 管理端布局:左侧栏导航 + 内容区;小屏(md 以下)侧栏折叠为图标栏
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  LayoutDashboard, Database, FileText, Settings, Cpu, ScrollText, LogOut,
} from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const nav = [
  { to: '/Dashboard', label: '仪表盘', icon: LayoutDashboard },
  { to: '/KnowledgeBases', label: '知识库', icon: Database },
  { to: '/Documents', label: '文档', icon: FileText },
  { to: '/RagConfig', label: 'RAG 配置', icon: Settings },
  { to: '/Models', label: '模型', icon: Cpu },
  { to: '/QaLogs', label: '问答日志', icon: ScrollText },
]

/** 当前激活项按路径前缀匹配(子路由/大小写不敏感场景均能命中) */
function isActive(to: string) {
  return route.path.toLowerCase() === to.toLowerCase()
}

async function onLogout() {
  await auth.logout()
  router.push('/Login')
}
</script>

<template>
  <!-- App-Shell:侧栏固定不随内容滚动,滚动条只属于内容区 -->
  <div class="flex h-screen overflow-hidden bg-muted/40">
    <!-- 侧栏:md 以下只留图标(w-14),md 起展开为 w-56 -->
    <aside class="flex h-full w-14 shrink-0 flex-col border-r bg-background md:w-56">
      <div class="hidden px-4 py-5 text-lg font-semibold md:block">管理后台</div>
      <div class="flex justify-center py-5 md:hidden">
        <LayoutDashboard class="h-5 w-5 text-muted-foreground" />
      </div>
      <nav class="flex-1 space-y-1 overflow-y-auto px-2">
        <router-link
          v-for="item in nav" :key="item.to" :to="item.to"
          class="relative flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent"
          :class="{ 'bg-accent font-medium': isActive(item.to) }"
          :title="item.label"
        >
          <!-- 当前项左侧 accent 条 -->
          <span
            v-if="isActive(item.to)"
            class="absolute left-0 top-1/2 h-4 w-1 -translate-y-1/2 rounded-full bg-primary"
          />
          <component :is="item.icon" class="h-4 w-4 shrink-0" />
          <span class="hidden md:inline">{{ item.label }}</span>
        </router-link>
      </nav>
      <button
        class="m-2 flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors hover:bg-accent"
        title="退出登录"
        @click="onLogout"
      >
        <LogOut class="h-4 w-4 shrink-0" />
        <span class="hidden md:inline">退出登录</span>
      </button>
    </aside>
    <!-- 内容区独立滚动:滚动不再"控制"侧边栏 -->
    <main class="min-w-0 flex-1 overflow-y-auto p-4 md:p-6">
      <router-view />
    </main>
  </div>
</template>
