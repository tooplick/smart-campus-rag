<script setup lang="ts">
// 管理页外壳:内容区顶部 5 项二级标签导航 + 内容滚动区
// 原 AdminLayout 的侧栏职责已拆给 TopNav(一级)+ 本标签栏(二级)
import { useRoute } from 'vue-router'
import { FileText, LayoutDashboard, ScrollText, Settings, Database } from '@lucide/vue'

const route = useRoute()

const tabs = [
    { to: '/Dashboard', label: '仪表盘', icon: LayoutDashboard },
    { to: '/KnowledgeBases', label: '知识库', icon: Database },
    { to: '/Documents', label: '文档', icon: FileText },
    { to: '/QaLogs', label: '问答日志', icon: ScrollText },
    { to: '/Settings', label: '设置', icon: Settings },
]

function isActive(to: string) {
    return route.path.toLowerCase() === to.toLowerCase()
}
</script>

<template>
    <div class="flex min-h-0 flex-1 flex-col">
        <!-- 二级标签:<768 横向滚动 -->
        <nav class="flex shrink-0 gap-1 overflow-x-auto border-b bg-background px-3 pt-2">
            <router-link v-for="tab in tabs" :key="tab.to" :to="tab.to"
                class="flex shrink-0 items-center gap-1.5 rounded-t-md px-3 py-2 text-sm transition-colors hover:bg-accent"
                :class="isActive(tab.to) ? 'bg-accent font-medium' : 'text-muted-foreground'">
                <component :is="tab.icon" class="h-4 w-4" /> {{ tab.label }}
            </router-link>
        </nav>
        <!-- 内容区独立滚动(原 AdminLayout main 的滚动/内边距职责) -->
        <div class="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
            <router-view />
        </div>
    </div>
</template>
