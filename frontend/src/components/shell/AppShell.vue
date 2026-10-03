<script setup lang="ts">
// 统一壳层:全宽顶栏 + 内容区;会话侧栏仅 /chat 渲染(其他页无聊天会话,不给展开入口)
// 侧栏响应式三档:≥1024 常驻(折叠偏好持久化);窄屏变抽屉,汉堡呼出浮层
import { computed, ref, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { useRoute } from 'vue-router'
import TopNav from './TopNav.vue'
import AppSidebar from './AppSidebar.vue'
import { readSidebarCollapsed, writeSidebarCollapsed } from '@/utils/sidebar'

const route = useRoute()
const wide = useMediaQuery('(min-width: 1024px)')
const collapsed = ref(readSidebarCollapsed())
const drawerOpen = ref(false)

/** 聊天会话侧栏只属于 Chat 页:其他页面(Home/Docs/管理页)不渲染、不出展开按钮 */
const showSidebar = computed(() => route.path === '/chat')

function toggleSidebar() {
    if (wide.value) {
        collapsed.value = !collapsed.value
        writeSidebarCollapsed(collapsed.value)
    } else {
        drawerOpen.value = !drawerOpen.value
    }
}

/** 传给侧栏的隐藏态:宽屏看折叠偏好,窄屏看抽屉开关 */
const sidebarHidden = computed(() => (wide.value ? collapsed.value : !drawerOpen.value))

// 路由切换后收起窄屏抽屉,避免遮挡新页面
watch(() => route.fullPath, () => { drawerOpen.value = false })
</script>

<template>
    <div class="flex h-screen flex-col overflow-hidden bg-background">
        <TopNav @toggle-sidebar="toggleSidebar" />
        <div class="relative flex min-h-0 flex-1">
            <!-- 窄屏抽屉背景遮罩(仅 Chat 页) -->
            <div v-if="showSidebar && !wide && drawerOpen" class="fixed inset-0 top-12 z-30 bg-black/40"
                @click="drawerOpen = false" />
            <AppSidebar v-if="showSidebar" :collapsed="sidebarHidden" @navigate="drawerOpen = false" />
            <main class="flex min-w-0 flex-1 flex-col overflow-hidden">
                <router-view />
            </main>
        </div>
    </div>
</template>
