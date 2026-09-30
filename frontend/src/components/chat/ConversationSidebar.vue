<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Plus, Pencil, Trash2, MessageSquare } from '@lucide/vue'
import { useChatStore } from '@/stores/chat'
import { Input } from '@/components/ui/input'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const chat = useChatStore()

const renamingId = ref<string | null>(null)
const renameText = ref('')
const deleteId = ref<string | null>(null)
const confirmOpen = ref(false)

onMounted(() => {
  chat.loadConversations().catch(() => {})
})

function startRename(id: string, title: string) {
  renamingId.value = id
  renameText.value = title
}

async function confirmRename(id: string) {
  if (renameText.value.trim()) await chat.renameConversation(id, renameText.value.trim())
  renamingId.value = null
}

function askDelete(id: string) {
  deleteId.value = id
  confirmOpen.value = true
}

async function onConfirmDelete() {
  if (deleteId.value) await chat.removeConversation(deleteId.value)
}
</script>

<template>
  <aside class="flex w-64 shrink-0 flex-col border-r">
    <div class="space-y-2 p-3">
      <button
        class="flex w-full items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent"
        @click="chat.newConversation()"
      >
        <Plus class="h-4 w-4" /> 新建会话
      </button>
    </div>
    <div class="flex-1 space-y-1 overflow-y-auto px-2">
      <div
        v-for="c in chat.conversations" :key="c.id"
        class="group flex items-center gap-1 rounded-md px-2 py-1.5 text-sm hover:bg-accent"
        :class="{ 'bg-accent': chat.currentConversationId === c.id }"
      >
        <template v-if="renamingId === c.id">
          <Input v-model="renameText" class="h-7" @keyup.enter="confirmRename(c.id)" @blur="confirmRename(c.id)" />
        </template>
        <template v-else>
          <MessageSquare class="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <button class="min-w-0 flex-1 truncate text-left" @click="chat.openConversation(c.id)">{{ c.title }}</button>
          <span class="hidden shrink-0 gap-0.5 group-hover:flex">
            <button class="rounded p-1 hover:bg-background" @click="startRename(c.id, c.title)"><Pencil class="h-3 w-3" /></button>
            <button class="rounded p-1 hover:bg-background" @click="askDelete(c.id)"><Trash2 class="h-3 w-3" /></button>
          </span>
        </template>
      </div>
    </div>
    <ConfirmDialog v-model:open="confirmOpen" title="删除会话" description="删除后不可恢复,确认删除该会话?" @confirm="onConfirmDelete" />
  </aside>
</template>
