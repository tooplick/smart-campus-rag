<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat.js'
import { Send } from '@lucide/vue'

const chatStore = useChatStore()
const emit = defineEmits<{
  send: [message: string]
}>()

const input = ref('')

function handleSend() {
  const msg = input.value.trim()
  if (!msg || chatStore.streaming) return
  emit('send', msg)
  input.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="border-t border-border bg-background px-6 py-4">
    <div class="flex items-end gap-3 max-w-3xl mx-auto">
      <textarea
        v-model="input"
        @keydown="handleKeydown"
        placeholder="输入你的问题..."
        rows="1"
        class="flex-1 resize-none rounded-xl border border-border px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary max-h-32 bg-background"
        :disabled="chatStore.streaming"
      />
      <button
        @click="handleSend"
        :disabled="!input.trim() || chatStore.streaming"
        class="flex items-center justify-center h-11 w-11 rounded-xl bg-primary text-primary-foreground disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
      >
        <Send class="h-5 w-5" />
      </button>
    </div>
  </div>
</template>
