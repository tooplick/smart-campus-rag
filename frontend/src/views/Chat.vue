<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useChatStore } from '@/stores/chat.js'
import { streamChat } from '@/api/chat.js'
import ChatShell from '@/components/chat/ChatShell.vue'
import WelcomePanel from '@/components/chat/WelcomePanel.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatComposer from '@/components/chat/ChatComposer.vue'
import SourceDrawer from '@/components/chat/SourceDrawer.vue'

const chatStore = useChatStore()
const sourceDrawerOpen = ref(false)
const activeSource = ref<any>(null)
let abortController: AbortController | null = null

onMounted(async () => {
  await chatStore.ensureClientId()
  await chatStore.loadKnowledgeBases()
})

async function handleNewConversation() {
  if (!chatStore.selectedKnowledgeBase) return
  await chatStore.newConversation(chatStore.selectedKnowledgeBase.id)
}

async function handleSendMessage(message: string) {
  if (!chatStore.selectedKnowledgeBase) return

  // If no active conversation, create one first
  if (!chatStore.activeConversationId) {
    const conv = await chatStore.newConversation(chatStore.selectedKnowledgeBase.id)
    if (!conv) return
  }

  // Add user message
  chatStore.addMessage('user', message)

  // Add AI message placeholder
  chatStore.addMessage('assistant', '')
  chatStore.streaming = true

  // SSE streaming request
  abortController = await streamChat(
    {
      conversation_id: chatStore.activeConversationId,
      knowledge_base_id: chatStore.selectedKnowledgeBase.id,
      message,
    },
    {
      onStart(data: any) {
        if (data.conversation_id) {
          chatStore.activeConversationId = data.conversation_id
        }
      },
      onToken(data: any) {
        chatStore.appendToken(data.token || data.content || '')
      },
      onSources(data: any) {
        const last = chatStore.messages[chatStore.messages.length - 1]
        if (last && last.role === 'assistant') {
          last.citations = data.sources || data.citations || []
        }
      },
      onDone() {
        chatStore.streaming = false
        chatStore.loadConversations()
      },
      onError(_data: any) {
        chatStore.streaming = false
        const last = chatStore.messages[chatStore.messages.length - 1]
        if (last && last.role === 'assistant' && !last.content) {
          last.content = '回答生成失败，请稍后重试。'
        }
      },
      onHttpError(_status: number, data: any) {
        chatStore.streaming = false
        const last = chatStore.messages[chatStore.messages.length - 1]
        if (last && last.role === 'assistant' && !last.content) {
          last.content = data?.message || '网络错误，请检查连接后重试。'
        }
      },
    }
  )
}

function handleViewSource(source: any) {
  activeSource.value = source
  sourceDrawerOpen.value = true
}
</script>

<template>
  <ChatShell @new-conversation="handleNewConversation">
    <template v-if="chatStore.activeConversationId || chatStore.messages.length > 0">
      <MessageList @view-source="handleViewSource" />
      <ChatComposer @send="handleSendMessage" />
    </template>
    <template v-else>
      <WelcomePanel
        @select-kb="(kb) => (chatStore.selectedKnowledgeBase = kb)"
        @send="handleSendMessage"
      />
    </template>
    <SourceDrawer
      v-model:open="sourceDrawerOpen"
      :source="activeSource"
    />
  </ChatShell>
</template>
