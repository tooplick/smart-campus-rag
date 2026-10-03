<script setup lang="ts">
// 来源文件卡:同文件的多个来源聚合为一张卡(文件为单位),点击滚动浏览全文
import { computed, ref } from 'vue'
import { toast } from 'vue-sonner'
import { Download, FileText } from '@lucide/vue'
import type { Source } from '@/api/types'
import { downloadDocument } from '@/api/documents'
import { Button } from '@/components/ui/button'
import SourcePreviewDialog from './SourcePreviewDialog.vue'

const props = defineProps<{ documentId: number; filename: string; sources: Source[] }>()
const previewOpen = ref(false)
const downloading = ref(false)

const score = computed(() => {
  const max = Math.max(...props.sources.map((s) => s.similarity_score))
  return `${(max * 100).toFixed(0)}%`
})
const pages = computed(() =>
  [...new Set(props.sources.map((s) => s.page_number).filter((p): p is number => p !== null))]
    .sort((a, b) => a - b),
)

async function onDownload() {
  if (downloading.value) return
  downloading.value = true
  try {
    await downloadDocument(props.documentId, props.filename)
  } catch {
    // 下载失败:顶部居中 toast 提示,不再弹二次对话框
    toast.error('下载失败,文件不存在或已删除')
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div tabindex="0" role="button"
    class="flex cursor-pointer items-start gap-2 rounded-md border bg-background p-2 text-xs hover:bg-accent/50"
    @click="previewOpen = true" @keydown.enter="previewOpen = true" @keydown.space.prevent="previewOpen = true">
    <FileText class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
    <div class="min-w-0 flex-1">
      <p class="truncate font-medium">{{ filename }}</p>
      <p class="text-muted-foreground">
        含 {{ sources.length }} 个来源<span v-if="pages.length"> · 第 {{ pages.join('、') }} 页</span> · 相似度 {{ score }}
      </p>
    </div>
    <Button variant="ghost" size="icon-sm" class="shrink-0" :disabled="downloading" aria-label="下载原文"
      @click.stop="onDownload">
      <Download />
    </Button>
    <SourcePreviewDialog v-model:open="previewOpen" :document-id="documentId" :filename="filename"
      :count="sources.length" />
  </div>
</template>
