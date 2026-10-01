<script setup lang="ts">
// 助手消息:Markdown 回答 + 参考来源(按文件聚合,每个文件一张卡,点击看全文)
import { computed } from 'vue'
import { AlertCircle } from '@lucide/vue'
import type { Source } from '@/api/types'
import type { UiMessage } from '@/stores/chat'
import MarkdownRenderer from './MarkdownRenderer.vue'
import CitationCard from './CitationCard.vue'
import StreamingIndicator from './StreamingIndicator.vue'

const props = defineProps<{ message: UiMessage }>()

/** 按文件聚合来源:同文件多来源合并为一张卡 */
const fileGroups = computed(() => {
  const map = new Map<number, { documentId: number; filename: string; sources: Source[] }>()
  for (const s of props.message.sources ?? []) {
    const g = map.get(s.document_id) ?? { documentId: s.document_id, filename: s.filename, sources: [] }
    g.sources.push(s)
    map.set(s.document_id, g)
  }
  return [...map.values()]
})
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
    <div v-if="fileGroups.length" class="flex flex-col gap-1.5">
      <p class="text-xs text-muted-foreground">参考来源</p>
      <CitationCard
        v-for="g in fileGroups"
        :key="g.documentId"
        :document-id="g.documentId"
        :filename="g.filename"
        :sources="g.sources"
      />
    </div>
  </div>
</template>
