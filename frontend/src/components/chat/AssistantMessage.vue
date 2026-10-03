<script setup lang="ts">
// 助手消息:Markdown 回答 + 参考来源(按文件聚合,每个文件一张卡,点击看全文)
import { computed } from 'vue'
import { Copy, TriangleAlert } from '@lucide/vue'
import { toast } from 'vue-sonner'
import type { Source } from '@/api/types'
import type { UiMessage } from '@/stores/chat'
import MarkdownRenderer from './MarkdownRenderer.vue'
import CitationCard from './CitationCard.vue'
import StreamingIndicator from './StreamingIndicator.vue'

const props = defineProps<{ message: UiMessage }>()
const emit = defineEmits<{ retry: [] }>()

/** 复制回答全文到剪贴板 */
async function copy() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    toast.success('已复制')
  } catch {
    toast.error('复制失败,请手动选择文本复制')
  }
}

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
  <div class="group/msg flex flex-col gap-2">
    <div v-if="message.content">
      <MarkdownRenderer :content="message.content" />
    </div>
    <StreamingIndicator v-else-if="message.streaming" />
    <!-- 失败:简短状态 + 重试入口(详细原因已顶部居中 toast 弹出) -->
    <div v-if="message.failed" class="flex flex-wrap items-center gap-2 text-sm text-destructive">
      <TriangleAlert class="h-4 w-4" /> 回答生成失败,可重试或检查模型配置
      <button class="rounded-md border px-2 py-0.5 text-xs text-foreground hover:bg-accent" @click="emit('retry')">
        重试发送
      </button>
    </div>
    <!-- 操作条:hover 显示复制 -->
    <div v-if="message.content && !message.streaming"
      class="flex opacity-0 transition-opacity group-hover/msg:opacity-100">
      <button class="flex items-center gap-1 rounded-md px-1.5 py-1 text-xs text-muted-foreground hover:bg-accent"
        @click="copy">
        <Copy class="h-3.5 w-3.5" /> 复制文字
      </button>
    </div>
    <div v-if="fileGroups.length" class="flex flex-col gap-1.5">
      <p class="text-xs text-muted-foreground">参考来源</p>
      <CitationCard v-for="g in fileGroups" :key="g.documentId" :document-id="g.documentId" :filename="g.filename"
        :sources="g.sources" />
    </div>
  </div>
</template>
