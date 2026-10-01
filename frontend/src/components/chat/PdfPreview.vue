<script setup lang="ts">
// PDF 预览:pdf.js 客户端渲染真实文件页面,文字层透明覆盖在画布上——
// 视觉是真实页面,文字可选中复制(浏览器 PDF 插件不可用的环境也稳定工作)
// 文字层按视觉阅读顺序(先行后列)排序,拖选与复制的文本顺序与视觉一致
import { onMounted, ref } from 'vue'
import * as pdfjs from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { Skeleton } from '@/components/ui/skeleton'

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl

const props = defineProps<{ documentId: number; filename: string }>()
const emit = defineEmits<{ error: [message: string] }>()

const wrap = ref<HTMLDivElement | null>(null)
const loading = ref(true)

/** 文字层条目:已换算到视口坐标 */
interface PositionedItem {
  str: string
  x: number
  y: number
  fontHeight: number
  fontFamily?: string
}

/** 把一行(基线相近)的条目按 x 排序后返回阅读顺序 */
function toReadingOrder(items: PositionedItem[]): PositionedItem[] {
  const lines: PositionedItem[][] = []
  for (const item of [...items].sort((a, b) => a.y - b.y)) {
    const line = lines.find((l) => Math.abs(l[0].y - item.y) <= 2)
    if (line) line.push(item)
    else lines.push([item])
  }
  return lines.flatMap((line) => line.sort((a, b) => a.x - b.x))
}

/** 按容器宽度渲染各页:画布与文字层同一坐标系,保证文字对齐可选 */
async function render() {
  loading.value = true
  try {
    const res = await fetch(`/api/files/${props.documentId}/view`)
    if (!res.ok) throw new Error()
    const data = await res.arrayBuffer()
    const doc = await pdfjs.getDocument({ data }).promise

    const host = wrap.value
    if (!host) return
    const width = host.clientWidth || 640
    host.innerHTML = ''

    for (let n = 1; n <= doc.numPages; n++) {
      const page = await doc.getPage(n)
      // 2 倍分辨率渲染保证清晰度,显示宽度仍为容器宽
      const scale = (width / page.getViewport({ scale: 1 }).width) * 2
      const viewport = page.getViewport({ scale })

      const canvas = document.createElement('canvas')
      canvas.width = viewport.width
      canvas.height = viewport.height
      canvas.style.width = '100%'
      canvas.style.display = 'block'
      await page.render({ canvas, viewport }).promise

      const holder = document.createElement('div')
      holder.className = 'relative mb-3 overflow-hidden rounded-md border bg-white'
      holder.appendChild(canvas)

      // 文字层:透明文字覆盖画布,仅供页内查找/无障碍;按内容保护要求禁选禁复制
      const textLayer = document.createElement('div')
      textLayer.className = 'absolute inset-0 overflow-hidden select-none'
      const content = await page.getTextContent()
      const items: PositionedItem[] = []
      for (const item of content.items) {
        if (!('str' in item) || !item.str) continue
        const tx = pdfjs.Util.transform(viewport.transform, item.transform)
        items.push({
          str: item.str,
          x: tx[4],
          y: tx[5],
          fontHeight: Math.hypot(tx[2], tx[3]),
          fontFamily: content.styles[item.fontName]?.fontFamily,
        })
      }
      for (const item of toReadingOrder(items)) {
        const span = document.createElement('span')
        span.textContent = item.str
        const style = span.style
        style.position = 'absolute'
        style.left = `${item.x}px`
        style.top = `${item.y - item.fontHeight}px`
        style.fontSize = `${item.fontHeight}px`
        style.lineHeight = '1'
        style.whiteSpace = 'pre'
        style.color = 'transparent'
        if (item.fontFamily) style.fontFamily = item.fontFamily
        textLayer.appendChild(span)
      }
      holder.appendChild(textLayer)
      host.appendChild(holder)
    }
  } catch {
    emit('error', 'PDF 加载失败,文件可能已被删除')
  } finally {
    loading.value = false
  }
}

onMounted(render)
defineExpose({ reload: render })
</script>

<template>
  <div>
    <div v-if="loading" class="space-y-3">
      <Skeleton v-for="i in 3" :key="i" class="h-40 w-full rounded-md" />
    </div>
    <!-- 内容保护:PDF 页整体禁止选中与复制 -->
    <div ref="wrap" class="pdf-preview-wrap select-none" @copy.prevent />
  </div>
</template>
