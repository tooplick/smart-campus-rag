<script setup lang="ts">
import MarkdownRenderer from './MarkdownRenderer.vue'
import CitationList from './CitationList.vue'
import StreamingIndicator from './StreamingIndicator.vue'

defineProps<{
  content: string
  citations?: Array<any>
  streaming?: boolean
}>()

const emit = defineEmits<{
  'view-source': [citation: any]
}>()
</script>

<template>
  <div class="flex mb-4">
    <div class="max-w-[80%] w-full">
      <div class="text-xs text-muted-foreground mb-1">AI 助手</div>
      <div class="bg-card border border-border px-4 py-3 rounded-2xl rounded-bl-md">
        <StreamingIndicator v-if="streaming && !content" />
        <MarkdownRenderer v-else-if="content" :content="content" />
        <CitationList :citations="citations || []" @view-source="emit('view-source', $event)" />
      </div>
    </div>
  </div>
</template>
