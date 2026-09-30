<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { UiMessage } from '@/stores/chat'
import UserMessage from './UserMessage.vue'
import AssistantMessage from './AssistantMessage.vue'

const props = defineProps<{ messages: UiMessage[] }>()
const root = ref<HTMLElement>()

watch(
  () => props.messages.map((m) => m.content.length).join(','),
  async () => {
    await nextTick()
    root.value?.scrollTo({ top: root.value.scrollHeight })
  },
)
</script>

<template>
  <div ref="root" class="flex-1 space-y-6 overflow-y-auto px-4 py-6">
    <template v-for="(m, i) in messages" :key="i">
      <UserMessage v-if="m.role === 'user'" :content="m.content" />
      <AssistantMessage v-else :message="m" />
    </template>
  </div>
</template>
