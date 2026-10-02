<script setup lang="ts">
// Chat 页(/chat):通栏对话布局,会话列表已提升到全局 AppSidebar
// 消息流铺满内容区,回答块限最大宽度;输入框吸底
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat'
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
  <div class="flex min-h-0 flex-1 flex-col">
    <WelcomePanel v-if="showWelcome" @ask="onSend" />
    <MessageList v-else :messages="chat.messages" />
    <ChatComposer :disabled="chat.sending" @send="onSend" />
  </div>
</template>
