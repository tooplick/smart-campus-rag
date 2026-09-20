<script setup lang="ts">
const props = defineProps<{
  citation: {
    document_name?: string
    filename?: string
    page_start?: number
    page_end?: number
    section?: string
    content?: string
  }
  index: number
}>()

const emit = defineEmits<{
  view: [citation: any]
}>()

function pageLabel() {
  if (props.citation.page_start && props.citation.page_end && props.citation.page_start !== props.citation.page_end) {
    return `第 ${props.citation.page_start}-${props.citation.page_end} 页`
  }
  if (props.citation.page_start) return `第 ${props.citation.page_start} 页`
  return ''
}
</script>

<template>
  <div
    class="flex items-start gap-2 p-2.5 rounded-lg border border-border bg-muted/30 hover:border-primary/30 cursor-pointer transition-colors"
    @click="emit('view', citation)"
  >
    <span class="flex-shrink-0 flex items-center justify-center h-5 w-5 rounded-full bg-primary/10 text-primary text-xs font-bold">
      {{ index }}
    </span>
    <div class="flex-1 min-w-0">
      <div class="text-xs font-medium text-foreground truncate">
        {{ citation.document_name || citation.filename || '未知文档' }}
      </div>
      <div class="text-xs text-muted-foreground mt-0.5">
        {{ pageLabel() }}
        <template v-if="citation.section"> · {{ citation.section }}</template>
      </div>
    </div>
    <span class="text-xs text-primary flex-shrink-0">查看</span>
  </div>
</template>
