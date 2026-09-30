<script setup lang="ts">
import { Sparkles } from '@lucide/vue'

const emit = defineEmits<{ ask: [q: string] }>()
const examples = ['本学期什么时候开学?', '图书馆开放时间是?', '如何申请奖学金?']
</script>

<template>
  <div class="flex flex-1 flex-col items-center justify-center gap-6">
    <Sparkles class="h-12 w-12 text-muted-foreground" />
    <div class="text-center">
      <h1 class="text-2xl font-semibold">智能校园知识库</h1>
      <p class="mt-2 text-muted-foreground">基于校园文档的智能问答,回答附带引用来源</p>
    </div>
    <div class="flex flex-wrap justify-center gap-2">
      <button
        v-for="q in examples" :key="q"
        class="rounded-full border px-4 py-2 text-sm hover:bg-accent"
        @click="emit('ask', q)"
      >
        {{ q }}
      </button>
    </div>
  </div>
</template>
