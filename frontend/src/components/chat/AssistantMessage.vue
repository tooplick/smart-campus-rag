<script setup lang="ts">
import { AlertCircle } from '@lucide/vue'
import type { UiMessage } from '@/stores/chat'
import MarkdownRenderer from './MarkdownRenderer.vue'
import CitationCard from './CitationCard.vue'
import StreamingIndicator from './StreamingIndicator.vue'

defineProps<{ message: UiMessage }>()
</script>

<template>
  <div class="flex flex-col gap-2">
    <div v-if="message.content">
      <MarkdownRenderer :content="message.content" />
    </div>
    <StreamingIndicator v-else-if="message.streaming" />
    <div v-if="message.error" class="flex items-center gap-1.5 text-sm text-destructive">
      <AlertCircle class="h-4 w-4" /> {{ message.error }}
    </div>
    <div v-if="message.sources?.length" class="flex flex-col gap-1.5">
      <p class="text-xs text-muted-foreground">参考来源</p>
      <CitationCard v-for="s in message.sources" :key="s.chunk_id" :source="s" />
    </div>
  </div>
</template>
