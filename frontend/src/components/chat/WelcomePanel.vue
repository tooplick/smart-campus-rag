<script setup lang="ts">
import { computed } from 'vue'
import { useChatStore } from '@/stores/chat.js'
import { ChevronDown } from '@lucide/vue'

const chatStore = useChatStore()
const emit = defineEmits<{
  'select-kb': [kb: any]
  send: [message: string]
}>()

const enabledKBs = computed(() =>
  chatStore.knowledgeBases.filter((kb: any) => kb.is_enabled)
)

const presetQuestions = [
  '补考什么时候报名？',
  '请假需要哪些材料？',
  '宿舍晚归如何处理？',
  '教务处在哪里？',
]

function selectKB(kb: any) {
  chatStore.selectedKnowledgeBase = kb
  emit('select-kb', kb)
}

function sendPreset(q: string) {
  emit('send', q)
}
</script>

<template>
  <div class="flex flex-1 items-center justify-center">
    <div class="w-full max-w-xl px-6 text-center">
      <h1 class="text-2xl font-bold text-foreground mb-2">校园知识库</h1>
      <p class="text-muted-foreground mb-8">问我校园规章、办事流程、通知和教务信息</p>

      <!-- KB Selector -->
      <div class="mb-8">
        <div class="relative inline-block">
          <select
            :value="chatStore.selectedKnowledgeBase?.id"
            @change="(e: Event) => {
              const target = e.target as HTMLSelectElement
              const kb = enabledKBs.find((k: any) => k.id === Number(target.value))
              if (kb) selectKB(kb)
            }"
            class="appearance-none bg-background border border-border rounded-lg px-4 py-2.5 pr-10 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
          >
            <option value="" disabled>选择知识库</option>
            <option v-for="kb in enabledKBs" :key="kb.id" :value="kb.id">
              {{ kb.name }}
            </option>
          </select>
          <ChevronDown class="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>
      </div>

      <!-- Preset Questions -->
      <div class="flex flex-wrap justify-center gap-2">
        <button
          v-for="q in presetQuestions"
          :key="q"
          @click="sendPreset(q)"
          class="px-4 py-2 rounded-lg border border-border text-sm text-muted-foreground hover:border-primary hover:text-primary hover:bg-primary/5 transition-colors"
        >
          {{ q }}
        </button>
      </div>
    </div>
  </div>
</template>
