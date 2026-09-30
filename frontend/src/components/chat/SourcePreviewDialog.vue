<script setup lang="ts">
import { computed } from 'vue'
import type { Source } from '@/api/types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'

const props = defineProps<{ source: Source; open: boolean }>()
const emit = defineEmits<{ 'update:open': [open: boolean] }>()

const score = computed(() => `${(props.source.similarity_score * 100).toFixed(0)}%`)
</script>

<template>
  <Dialog :open="props.open" @update:open="emit('update:open', $event)">
    <DialogContent class="sm:max-w-2xl">
      <DialogHeader>
        <DialogTitle class="truncate">{{ source.filename }}</DialogTitle>
        <DialogDescription>
          <span v-if="source.page_number !== null">第 {{ source.page_number }} 页 · </span>
          <span v-if="source.section_title">{{ source.section_title }} · </span>
          相似度 {{ score }}
        </DialogDescription>
      </DialogHeader>
      <ScrollArea class="max-h-[60vh] pr-3">
        <p v-if="source.content" class="whitespace-pre-wrap text-sm leading-relaxed">
          {{ source.content }}
        </p>
        <p v-else class="text-sm text-muted-foreground">暂无切片内容</p>
      </ScrollArea>
    </DialogContent>
  </Dialog>
</template>
