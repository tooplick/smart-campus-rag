<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '@/stores/chat.js'
import UserMessage from './UserMessage.vue'
import AssistantMessage from './AssistantMessage.vue'

const chatStore = useChatStore()
const scrollRef = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight
    }
  })
}

watch(
  () => chatStore.messages.length,
  scrollToBottom
)

watch(
  () => {
    const last = chatStore.messages[chatStore.messages.length - 1]
    return last?.content?.length || 0
  },
  scrollToBottom
)

const emit = defineEmits<{
  'view-source': [citation: any]
}>()
</script>

<template>
  <div ref="scrollRef" class="flex-1 overflow-y-auto px-6 py-4">
    <div class="max-w-3xl mx-auto">
      <template v-for="(msg, i) in chatStore.messages" :key="i">
        <UserMessage v-if="msg.role === 'user'" :content="msg.content" />
        <AssistantMessage
          v-else
          :content="msg.content"
          :citations="msg.citations || []"
          :streaming="chatStore.streaming && i === chatStore.messages.length - 1"
          @view-source="emit('view-source', $event)"
        />
      </template>
    </div>
  </div>
</template>
