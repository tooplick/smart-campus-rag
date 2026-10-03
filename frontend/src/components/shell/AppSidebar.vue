<script setup lang="ts">
// 全局左侧栏(260px):上半会话区(匿名 X-Client-ID,访客照常可用)+ 底部账号区钉底
// 会话列表逻辑迁自原 ConversationSidebar;数据经 chat store 与 ChatView 共享
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { LogIn, LogOut, MessageSquare, Pencil, Plus, Trash2 } from '@lucide/vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { errorMessage } from '@/utils/request'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const props = defineProps<{ collapsed: boolean }>()
const emit = defineEmits<{ navigate: [] }>()

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()

const renamingId = ref<string | null>(null)
const renameText = ref('')
const deleteId = ref<string | null>(null)
const confirmOpen = ref(false)

onMounted(() => {
    chat.loadConversations().catch((e) => toast.error(errorMessage(e)))
})

function startRename(id: string, title: string) {
    renamingId.value = id
    renameText.value = title
}

async function confirmRename(id: string) {
    try {
        if (renameText.value.trim()) await chat.renameConversation(id, renameText.value.trim())
    } catch (e) {
        toast.error(errorMessage(e))
    } finally {
        renamingId.value = null
    }
}

function askDelete(id: string) {
    deleteId.value = id
    confirmOpen.value = true
}

async function onConfirmDelete() {
    if (!deleteId.value) return
    try {
        await chat.removeConversation(deleteId.value)
    } catch (e) {
        toast.error(errorMessage(e))
    }
}

/** 切换会话:Chat 页内即时生效;其他页先跳转到 /chat */
async function openConversation(id: string) {
    try {
        await chat.openConversation(id)
    } catch (e) {
        toast.error(errorMessage(e))
        return
    }
    if (route.path !== '/chat') router.push('/chat')
    emit('navigate')
}

function newConversation() {
    chat.newConversation()
    if (route.path !== '/chat') router.push('/chat')
    emit('navigate')
}

async function onLogout() {
    await auth.logout()
    emit('navigate')
    router.push('/')
}
</script>

<template>
    <!-- 窄屏:fixed 抽屉浮层(平移进出,不挤压内容区);≥1024:static 常驻栏,折叠收为 0 宽 -->
    <aside
        class="fixed bottom-0 left-0 top-12 z-40 h-full w-64 shrink-0 overflow-hidden border-r bg-background shadow-lg transition-[width,transform] duration-200 lg:static lg:z-auto lg:shadow-none"
        :class="[
            props.collapsed ? '-translate-x-full lg:translate-x-0 lg:w-0' : 'translate-x-0 lg:w-64',
        ]" :aria-hidden="props.collapsed">
        <div class="flex h-full w-64 flex-col">
            <!-- 上半:会话区 -->
            <div class="flex min-h-0 flex-1 flex-col">
                <div class="space-y-2 p-3">
                    <button class="flex w-full items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent"
                        @click="newConversation">
                        <Plus class="h-4 w-4" /> 新建会话
                    </button>
                </div>
                <div class="min-h-0 flex-1 space-y-1 overflow-y-auto px-2">
                    <div v-for="c in chat.conversations" :key="c.id"
                        class="group flex items-center gap-1 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
                        :class="{ 'bg-accent': chat.currentConversationId === c.id }">
                        <template v-if="renamingId === c.id">
                            <Input v-model="renameText" class="h-7" @keyup.enter="confirmRename(c.id)"
                                @blur="confirmRename(c.id)" />
                        </template>
                        <template v-else>
                            <MessageSquare class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            <button class="min-w-0 flex-1 truncate text-left" @click="openConversation(c.id)">{{ c.title
                            }}</button>
                            <span class="hidden shrink-0 gap-0.5 group-hover:flex">
                                <button class="rounded p-1 hover:bg-background" @click="startRename(c.id, c.title)">
                                    <Pencil class="h-3 w-3" />
                                </button>
                                <button class="rounded p-1 hover:bg-background" @click="askDelete(c.id)">
                                    <Trash2 class="h-3 w-3" />
                                </button>
                            </span>
                        </template>
                    </div>
                </div>
            </div>

            <!-- 底部账号区钉底:访客「登录」;管理员用户名 + 退出 -->
            <div class="border-t p-3">
                <Button v-if="!auth.token" variant="outline" class="w-full justify-start"
                    @click="router.push('/Login'); emit('navigate')">
                    <LogIn class="mr-2 h-4 w-4" /> 登录
                </Button>
                <div v-else class="flex items-center justify-between gap-2">
                    <span class="min-w-0 truncate text-sm text-muted-foreground">{{ auth.username || 'admin' }}</span>
                    <button class="rounded-md p-1.5 text-muted-foreground hover:bg-accent" title="退出登录"
                        @click="onLogout">
                        <LogOut class="h-4 w-4" />
                    </button>
                </div>
            </div>

            <ConfirmDialog v-model:open="confirmOpen" title="删除会话" description="删除后不可恢复,确认删除该会话?"
                @confirm="onConfirmDelete" />
        </div>
    </aside>
</template>
