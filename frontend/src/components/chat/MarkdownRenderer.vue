<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps<{ content: string }>()

const md = new MarkdownIt({ breaks: true, linkify: true })

/** 将回答中的 [来源 N] 标记渲染为引用角标 */
function highlightMarkers(html: string): string {
  return html.replace(
    /\[(\d+|来源\s*\d+)\]/g,
    (_m, p1: string) => {
      const n = (p1.match(/\d+/) ?? [''])[0]
      return `<sup class="ml-0.5 rounded bg-accent px-1 text-xs text-accent-foreground" data-cite="${n}">${n}</sup>`
    },
  )
}

const html = computed(() => highlightMarkers(md.render(props.content)))
</script>

<template>
  <!-- 内容来自受控 LLM 输出 -->
  <div class="prose prose-sm dark:prose-invert max-w-none" v-html="html" />
</template>
