<script setup lang="ts">
import { Copy } from '@lucide/vue'
import { toast } from 'vue-sonner'

const props = defineProps<{ content: string }>()

/** 复制提问原文到剪贴板 */
async function copy() {
  try {
    await navigator.clipboard.writeText(props.content)
    toast.success('已复制')
  } catch {
    toast.error('复制失败,请手动选择文本复制')
  }
}
</script>

<template>
  <div class="group flex items-start justify-end gap-2">
    <button
      class="mt-1 flex shrink-0 items-center gap-1 rounded-md px-1.5 py-1 text-xs text-muted-foreground opacity-0 transition-opacity hover:bg-accent group-hover:opacity-100"
      aria-label="复制文字" @click="copy">
      <Copy class="h-3.5 w-3.5" /> 复制文字
    </button>
    <div class="max-w-[80%] whitespace-pre-wrap rounded-2xl bg-primary px-4 py-2 text-sm text-primary-foreground">
      {{ content }}
    </div>
  </div>
</template>
