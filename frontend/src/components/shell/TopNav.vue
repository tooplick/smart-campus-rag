<script setup lang="ts">
// 全宽顶栏:Logo(回首页)/ 四项一级导航(Dashboard 仅登录可见)/ 账号入口
// <md 断点导航收纳进右侧菜单;汉堡按钮负责侧栏折叠(AppShell 状态)
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { GraduationCap, LogIn, LogOut, Menu } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
import { Button } from '@/components/ui/button'
import {
    DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const emit = defineEmits<{ 'toggle-sidebar': [] }>()

/** 一级导航;Dashboard 仅登录管理员可见 */
const nav = computed(() => [
    { to: '/', label: 'Home' },
    { to: '/docs', label: 'Docs' },
    { to: '/chat', label: 'Chat' },
    ...(auth.token ? [{ to: '/Dashboard', label: 'Dashboard' }] : []),
])

/** 当前页高亮:精确匹配公共页;管理页(Dashboard 项)按 meta.admin 归并 */
function isActive(to: string) {
    if (to === '/Dashboard') return route.meta.admin === true
    return route.path === to
}

async function onLogout() {
    await auth.logout()
    router.push('/')
}
</script>

<template>
    <header class="flex h-12 shrink-0 items-center gap-2 border-b bg-background px-3">
        <!-- 汉堡:桌面折叠侧栏,窄屏呼出抽屉 -->
        <Button variant="ghost" size="icon" aria-label="切换侧栏" @click="emit('toggle-sidebar')">
            <Menu class="h-4 w-4" />
        </Button>

        <router-link to="/" class="flex items-center gap-1.5 text-sm font-semibold">
            <GraduationCap class="h-5 w-5" /> 校园知识库
        </router-link>

        <!-- md 起:导航胶囊平铺 -->
        <nav class="ml-auto hidden items-center gap-1 md:flex">
            <router-link v-for="item in nav" :key="item.to" :to="item.to"
                class="rounded-full px-3 py-1.5 text-sm transition-colors hover:bg-accent"
                :class="isActive(item.to) ? 'bg-accent font-medium' : 'text-muted-foreground'">
                {{ item.label }}
            </router-link>
        </nav>

        <div class="ml-auto flex items-center gap-2 md:ml-2">
            <!-- <md:导航与账号统一收纳 -->
            <DropdownMenu>
                <DropdownMenuTrigger class="rounded-md p-2 hover:bg-accent md:hidden" aria-label="菜单">
                    <Menu class="h-4 w-4" />
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                    <DropdownMenuItem v-for="item in nav" :key="item.to" @click="router.push(item.to)">
                        {{ item.label }}
                    </DropdownMenuItem>
                    <DropdownMenuItem v-if="!auth.token" @click="router.push('/Login')">
                        <LogIn class="mr-2 h-4 w-4" /> 登录
                    </DropdownMenuItem>
                    <DropdownMenuItem v-else @click="onLogout">
                        <LogOut class="mr-2 h-4 w-4" /> 退出登录
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>

            <!-- 账号入口:未登录「登录」;已登录「管理员 ▾」 -->
            <Button v-if="!auth.token" variant="outline" size="sm" @click="router.push('/Login')">
                <LogIn class="mr-1.5 h-4 w-4" /> 登录
            </Button>
            <DropdownMenu v-else>
                <DropdownMenuTrigger
                    class="hidden items-center gap-1 rounded-md px-2.5 py-1.5 text-sm hover:bg-accent md:flex">
                    管理员
                    <span class="text-xs text-muted-foreground">▾</span>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                    <DropdownMenuItem disabled>{{ auth.username || 'admin' }}</DropdownMenuItem>
                    <DropdownMenuItem @click="onLogout">
                        <LogOut class="mr-2 h-4 w-4" /> 退出登录
                    </DropdownMenuItem>
                </DropdownMenuContent>
            </DropdownMenu>
        </div>
    </header>
</template>
