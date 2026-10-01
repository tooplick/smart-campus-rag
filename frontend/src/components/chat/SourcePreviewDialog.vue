<script setup lang="ts">
// 来源预览弹层:直接展示原始文件本体(不拼接加工)
// PDF → 服务端逐页渲染图片堆叠 + 滚动浏览(浏览器 PDF 插件在部分环境不可用,iframe 会黑屏)
// 图片 → 原图;文本类 → 原文;Office 类浏览器渲染不了 → 下载引导
import { computed, ref, watch } from 'vue'
import { Download, FileText } from '@lucide/vue'
import { documentViewUrl, downloadDocument, fetchDocumentRawText } from '@/api/documents'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import PdfPreview from './PdfPreview.vue'
import { Button } from '@/components/ui/button'

const props = defineProps<{
  open: boolean
  documentId: number
  filename: string
  count: number
}>()
const emit = defineEmits<{ 'update:open': [open: boolean] }>()

const ext = computed(() => props.filename.split('.').pop()?.toLowerCase() ?? '')
const kind = computed<'pdf' | 'image' | 'text' | 'download'>(() => {
  if (ext.value === 'pdf') return 'pdf'
  if (['png', 'jpg', 'jpeg'].includes(ext.value)) return 'image'
  if (['txt', 'md', 'csv', 'html', 'htm'].includes(ext.value)) return 'text'
  return 'download'
})

const loading = ref(false)
const error = ref('')
const rawText = ref('')
const viewUrl = computed(() => documentViewUrl(props.documentId))
/** PDF 由 PdfPreview(pdf.js)自行加载渲染,文字层可选中复制 */
const pdfKey = ref(0)

async function load() {
  loading.value = true
  error.value = ''
  try {
    if (kind.value === 'text') {
      rawText.value = await fetchDocumentRawText(props.documentId)
    }
  } catch {
    error.value = '文件获取失败,可能已被删除'
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (v) => {
    if (v && kind.value === 'pdf') pdfKey.value++
    if (v && !rawText.value && !loading.value && kind.value === 'text') load()
  },
)

const downloading = ref(false)
async function onDownload() {
  if (downloading.value) return
  downloading.value = true
  try {
    await downloadDocument(props.documentId, props.filename)
  } catch {
    error.value = '下载失败,文件不存在或已删除'
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <Dialog :open="props.open" @update:open="emit('update:open', $event)">
    <!-- 内容保护:预览区禁止选中与复制 -->
    <DialogContent class="sm:max-w-2xl select-none" @copy.prevent @cut.prevent>
      <DialogHeader>
        <DialogTitle class="truncate">{{ filename }}</DialogTitle>
        <DialogDescription>共 {{ count }} 个来源 · 滚动浏览原文件全文</DialogDescription>
      </DialogHeader>

      <!-- PDF:pdf.js 渲染真实页面 + 文字层,滚动浏览且文字可选中复制 -->
      <ScrollArea v-if="kind === 'pdf' && !error" class="max-h-[60vh] pr-3">
        <PdfPreview :key="pdfKey" :document-id="documentId" :filename="filename" @error="error = $event" />
      </ScrollArea>
      <!-- 图片:原图展示 -->
      <div v-else-if="kind === 'image' && !error" class="flex max-h-[60vh] justify-center overflow-auto rounded-md border">
        <img :src="viewUrl" :alt="filename" class="max-h-[60vh] object-contain" />
      </div>
      <!-- 文本类:原文展示 -->
      <ScrollArea v-else-if="kind === 'text' && !error" class="max-h-[60vh] pr-3">
        <div v-if="loading" class="space-y-2 py-1">
          <Skeleton v-for="i in 6" :key="i" class="h-4" :class="i % 3 === 0 ? 'w-2/3' : 'w-full'" />
        </div>
        <p v-else-if="rawText" class="whitespace-pre-wrap text-sm leading-relaxed">{{ rawText }}</p>
        <p v-else class="text-sm text-muted-foreground">暂无内容</p>
      </ScrollArea>
      <!-- Office 等:浏览器无法内联渲染,给下载引导 -->
      <div v-else-if="kind === 'download' && !error" class="flex flex-col items-start gap-3 py-6">
        <p class="flex items-center gap-2 text-sm text-muted-foreground">
          <FileText class="h-4 w-4" /> 浏览器暂不支持在线预览该格式,请下载查看
        </p>
        <Button :disabled="downloading" @click="onDownload">
          <Download class="mr-1 h-4 w-4" /> {{ downloading ? '下载中…' : '下载文件' }}
        </Button>
      </div>
      <!-- 错误态 -->
      <div v-if="error" class="flex flex-col items-start gap-2 py-4 text-sm">
        <p class="text-destructive">{{ error }}</p>
        <button class="rounded-md border px-3 py-1.5 text-sm hover:bg-accent" @click="load">重试</button>
      </div>
    </DialogContent>
  </Dialog>
</template>
