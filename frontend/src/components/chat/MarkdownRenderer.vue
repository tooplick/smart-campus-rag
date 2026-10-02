<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps<{ content: string }>()

/** Chat 模式:开启 [来源 N] 引用角标高亮 */
const html = computed(() => renderMarkdown(props.content, true))
</script>

<template>
  <!-- 内容来自受控 LLM 输出 -->
  <div class="prose prose-sm dark:prose-invert max-w-none" v-html="html" />
</template>
