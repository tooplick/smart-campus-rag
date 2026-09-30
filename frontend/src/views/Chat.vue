<script setup lang="ts">
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
import ConversationSidebar from '@/components/chat/ConversationSidebar.vue'
import WelcomePanel from '@/components/chat/WelcomePanel.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatComposer from '@/components/chat/ChatComposer.vue'

const chat = useChatStore()
const showWelcome = computed(() => chat.messages.length === 0)

function onSend(content: string) {
  chat.send(content)
}
</script>

<template>
  <div class="flex h-screen">
    <ConversationSidebar />
    <div class="flex min-w-0 flex-1 flex-col">
      <WelcomePanel v-if="showWelcome" @ask="onSend" />
      <MessageList v-else :messages="chat.messages" />
      <ChatComposer :disabled="chat.sending" @send="onSend" />
    </div>
  </div>
</template>
