<script setup lang="ts">
import { onMounted } from 'vue'
import { useChatStore } from '@/stores/chat.js'
import { updateConversation } from '@/api/conversations.js'
import { Plus } from '@lucide/vue'
import ConversationItem from './ConversationItem.vue'

const chatStore = useChatStore()

const emit = defineEmits<{
  'new-conversation': []
}>()

onMounted(() => {
  chatStore.loadConversations()
})

function handleSelect(id: string) {
  chatStore.resumeConversation(id)
}

function handleRename(conversation: { id: string; title: string }) {
  const newTitle = prompt('重命名会话', conversation.title)
  if (newTitle && newTitle !== conversation.title) {
    updateConversation(conversation.id, newTitle).then(() => {
      conversation.title = newTitle
    })
  }
}

async function handleDelete(id: string) {
  if (confirm('确定删除此会话？')) {
    await chatStore.removeConversation(id)
  }
}
</script>

<template>
  <div class="flex h-full w-64 flex-col border-r border-border bg-muted/30">
    <div class="flex items-center justify-between px-4 py-4 border-b border-border">
      <span class="text-sm font-semibold text-foreground">对话</span>
      <button
        @click="emit('new-conversation')"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
      >
        <Plus class="h-3.5 w-3.5" />
        新建
      </button>
    </div>
    <div class="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
      <ConversationItem
        v-for="c in chatStore.conversations"
        :key="c.id"
        :conversation="c"
        :active="c.id === chatStore.activeConversationId"
        @select="handleSelect"
        @rename="handleRename"
        @delete="handleDelete"
      />
      <div
        v-if="chatStore.conversations.length === 0"
        class="flex items-center justify-center h-32 text-sm text-muted-foreground"
      >
        暂无对话
      </div>
    </div>
  </div>
</template>
