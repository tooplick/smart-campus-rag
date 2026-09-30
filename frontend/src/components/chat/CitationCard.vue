<script setup lang="ts">
import { computed, ref } from 'vue'
import { Download, FileText } from '@lucide/vue'
import type { Source } from '@/api/types'
import { downloadDocument } from '@/api/documents'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import SourcePreviewDialog from './SourcePreviewDialog.vue'

const props = defineProps<{ source: Source }>()
const score = computed(() => `${(props.source.similarity_score * 100).toFixed(0)}%`)
const previewOpen = ref(false)
const downloading = ref(false)
const errorOpen = ref(false)

async function onDownload() {
  if (downloading.value) return
  downloading.value = true
  try {
    await downloadDocument(props.source.document_id, props.source.filename)
  } catch {
    errorOpen.value = true
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <div
    tabindex="0"
    role="button"
    class="flex cursor-pointer items-start gap-2 rounded-md border bg-background p-2 text-xs hover:bg-accent/50"
    @click="previewOpen = true"
    @keydown.enter="previewOpen = true"
    @keydown.space.prevent="previewOpen = true"
  >
    <FileText class="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
    <div class="min-w-0 flex-1">
      <p class="truncate font-medium">{{ source.filename }}</p>
      <p class="text-muted-foreground">
        <span v-if="source.page_number !== null">第 {{ source.page_number }} 页 · </span>
        <span v-if="source.section_title">{{ source.section_title }} · </span>
        相似度 {{ score }}
      </p>
    </div>
    <Button
      variant="ghost"
      size="icon-sm"
      class="shrink-0"
      :disabled="downloading"
      aria-label="下载原文"
      @click.stop="onDownload"
    >
      <Download />
    </Button>
    <span class="shrink-0 rounded bg-accent px-1 text-accent-foreground">{{ source.source_order }}</span>
    <SourcePreviewDialog v-model:open="previewOpen" :source="source" />
    <AlertDialog v-model:open="errorOpen">
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>下载失败</AlertDialogTitle>
          <AlertDialogDescription>文件不存在或已删除</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogAction>知道了</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  </div>
</template>
