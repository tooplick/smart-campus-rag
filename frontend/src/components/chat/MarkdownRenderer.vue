<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const props = defineProps<{
  content: string
}>()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
})

const rendered = computed(() => {
  if (!props.content) return ''
  return md.render(props.content)
})
</script>

<template>
  <div
    class="prose prose-sm max-w-none prose-headings:font-semibold prose-a:text-primary prose-a:no-underline hover:prose-a:underline prose-code:bg-muted prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-pre:bg-muted prose-pre:rounded-lg"
    v-html="rendered"
  />
</template>
